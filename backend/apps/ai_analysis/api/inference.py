"""Authenticated API for creating and reading real AI analyses."""

from django.http import Http404
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.models import RolePermission
from apps.ai_analysis.models import AIAnalysis, AIAnalysisInputSeries, AIAnalysisResult, AIModelConfigVersion, AIResultArtifact, AIResultReview, AIRoutingConfigVersion, ModelVersion
from apps.ai_analysis.api.generated_real_149 import ContractView000
from apps.ai_analysis.services.inference import create_queued_analysis, transition_analysis
from apps.ai_analysis.tasks.inference import ROLE_ORDER, run_analysis_inference
from apps.imaging.models import ImagingStudy, NiftiArtifact
from apps.imaging.services.nifti import open_gcs_uri


CLINICAL_AI_ROLES = {"NEUROLOGIST", "NEUROSURGEON", "RADIOLOGY"}


class InputArtifactSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["CT", "DWI", "ADC", "MRA"])
    uri = serializers.RegexField(r"^gs://[^/]+/.+", max_length=1024)
    size_bytes = serializers.IntegerField(min_value=1)
    sha256 = serializers.RegexField(r"^[a-f0-9]{64}$")


class AnalysisCreateSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    model_version_id = serializers.UUIDField(required=False)
    model_config_version_id = serializers.UUIDField(required=False)
    analysis_type = serializers.ChoiceField(choices=list(ROLE_ORDER))
    priority = serializers.ChoiceField(choices=["NORMAL", "HIGH", "CRITICAL"], default="NORMAL")
    series_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=2, required=False)
    inputs = InputArtifactSerializer(many=True, min_length=1, max_length=2, required=False)

    def validate(self, attrs):
        routing = AIRoutingConfigVersion.objects.filter(
            analysis_type=attrs["analysis_type"], is_active=True
        ).select_related("target_model_version__model").order_by("-created_at").first()
        requested_version_id = attrs.get("model_version_id")
        version = ModelVersion.objects.filter(
            pk=requested_version_id or (routing.target_model_version_id if routing else None),
            is_active=True, validation_status="APPROVED"
        ).select_related("model").first()
        if version is None:
            raise serializers.ValidationError({"model_version_id": "Approved model version not found."})
        config_query = AIModelConfigVersion.objects.filter(model_version=version, is_active=True)
        config_id = attrs.get("model_config_version_id")
        config = config_query.filter(pk=config_id).first() if config_id else config_query.order_by("-created_at").first()
        if config is None:
            raise serializers.ValidationError({"model_config_version_id": "Active model config not found."})
        study = ImagingStudy.objects.filter(pk=attrs["study_id"], status="AVAILABLE").first()
        if study is None:
            raise serializers.ValidationError({"study_id": "Available study not found."})
        inputs = attrs.get("inputs")
        series_ids = attrs.get("series_ids")
        if inputs is None and series_ids:
            artifacts = NiftiArtifact.objects.filter(
                series_id__in=series_ids, series__study=study
            )
            by_role = {item.role: item for item in artifacts}
            expected_roles = list(ROLE_ORDER[attrs["analysis_type"]])
            inputs = [
                {"role": role, "uri": by_role[role].uri, "size_bytes": by_role[role].size_bytes, "sha256": by_role[role].sha256}
                for role in expected_roles if role in by_role
            ]
        if not inputs:
            raise serializers.ValidationError({"series_ids": "Registered NIfTI input series are required."})
        roles = [item["role"] for item in inputs]
        expected = list(ROLE_ORDER[attrs["analysis_type"]])
        if roles != expected:
            raise serializers.ValidationError({"inputs": f"roles must be {expected} in order"})
        attrs.update(model_version=version, model_config_version=config, routing_config_version=routing, study=study, inputs=inputs)
        return attrs


def analysis_payload(analysis):
    result = AIAnalysisResult.objects.filter(analysis=analysis).first()
    return {
        "analysis_id": str(analysis.id),
        "study_id": str(analysis.study_id),
        "analysis_type": analysis.analysis_type,
        "status": analysis.status,
        "stage": analysis.stage,
        "attempt_count": analysis.attempt_count,
        "failure_code": analysis.failure_code,
        "trace_id": analysis.trace,
        "priority": analysis.priority,
        "requested_at": analysis.requested_at,
        "completed_at": analysis.completed_at,
        "model": {
            "code": analysis.model_version.model.code,
            "version": analysis.model_version.version,
        },
        "result": result.structured_findings if result else None,
    }


def _can_read_analysis(request, analysis):
    role_code = getattr(getattr(request.user, "role", None), "code", None)
    return role_code in CLINICAL_AI_ROLES and (
        analysis.requested_by_id == request.user.id or request.user.is_staff
    )


class AnalysisCollectionView(ContractView000):
    """List real inference jobs and accept new inference requests."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, "role", None)
        role_code = getattr(role, "code", None)

        if role_code in CLINICAL_AI_ROLES:
            analyses = AIAnalysis.objects.filter(requested_by=request.user)
        elif role_code == "SYSTEM_ADMIN":
            has_job_view = RolePermission.objects.filter(
                role=role,
                permission__code="ai.job.view",
            ).exists()
            if not has_job_view:
                raise PermissionDenied({
                    "code": "AI_ANALYSIS_LIST_FORBIDDEN",
                    "detail": "The current role cannot view AI analysis jobs.",
                })
            analyses = AIAnalysis.objects.all()
        else:
            raise PermissionDenied({
                "code": "AI_ANALYSIS_LIST_FORBIDDEN",
                "detail": "The current role cannot view AI analysis jobs.",
            })

        requested_status = request.query_params.get("status")
        if requested_status:
            analyses = analyses.filter(status=requested_status)
        analyses = analyses.select_related("model_version__model").order_by("-requested_at")
        rows = [analysis_payload(analysis) for analysis in analyses[:100]]
        return Response({"count": analyses.count(), "next": None, "previous": None, "results": rows})
    @extend_schema(
        request=AnalysisCreateSerializer,
        responses={202: None},
    )
    def post(self, request):
        serializer = AnalysisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        analysis = create_queued_analysis(
            study=values["study"],
            model_version=values["model_version"],
            model_config_version=values["model_config_version"],
            requested_by=request.user,
            analysis_type=values["analysis_type"],
            priority=values["priority"],
            inputs=values["inputs"],
            series_ids=values.get("series_ids"),
            routing_config_version=values.get("routing_config_version"),
        )
        try:
            run_analysis_inference.apply_async(args=[str(analysis.id)], retry=False)
        except (OperationalError, OSError):
            transition_analysis(
                analysis,
                status="FAILED",
                stage="VALIDATING",
                reason_code="BROKER_UNAVAILABLE",
            )
            return Response(analysis_payload(analysis), status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(analysis_payload(analysis), status=status.HTTP_202_ACCEPTED)


class AnalysisDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, analysis_id):
        analysis = AIAnalysis.objects.filter(pk=analysis_id).first()
        if analysis is None:
            raise Http404
        if analysis.requested_by_id != request.user.id and not request.user.is_staff:
            raise Http404
        return Response(analysis_payload(analysis))


class AnalysisResultView(APIView):
    """Return the persisted inference result for the React result screen."""

    permission_classes = [IsAuthenticated]

    def get(self, request, analysis_id):
        analysis = AIAnalysis.objects.filter(pk=analysis_id).first()
        if analysis is None or not _can_read_analysis(request, analysis):
            raise Http404

        result = AIAnalysisResult.objects.filter(analysis=analysis).first()
        if result is None:
            return Response(
                {
                    "code": "AI_RESULT_NOT_READY",
                    "detail": "The analysis result is not ready yet.",
                    "status": analysis.status,
                    "stage": analysis.stage,
                },
                status=status.HTTP_409_CONFLICT,
            )

        findings = result.structured_findings or {}
        latest_review = AIResultReview.objects.filter(result=result).order_by("-reviewed_at").first()
        artifacts = AIResultArtifact.objects.filter(result=result).order_by("created_at")
        return Response(
            {
                "analysis_id": str(analysis.id),
                "result_id": str(result.id),
                "output_schema_version": findings.get("output_schema_version", "1.0"),
                "is_positive": result.is_positive,
                "confidence": result.confidence,
                "threshold_used": findings.get("threshold_used"),
                "lesion_count": result.lesion_count,
                "total_volume_ml": result.total_volume_ml,
                "severity": result.severity,
                "structured_findings": findings,
                "artifacts": [
                    {
                        "artifact_id": str(item.id),
                        "type": item.artifact_type,
                        "sop_instance_uid": (
                            str(item.dicom_object_reference_id)
                            if item.dicom_object_reference_id
                            else ""
                        ),
                    }
                    for item in artifacts
                ],
                "latest_review": (
                    {"decision": latest_review.decision}
                    if latest_review is not None
                    else None
                ),
            }
        )


class AnalysisNiftiViewerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, analysis_id):
        analysis = AIAnalysis.objects.filter(pk=analysis_id).first()
        if analysis is None or not _can_read_analysis(request, analysis):
            raise Http404
        series_ids = AIAnalysisInputSeries.objects.filter(analysis=analysis).values_list("series_id", flat=True)
        inputs = [
            {
                "role": item.role,
                "url": f"/api/v1/nifti-artifacts/{item.id}/content",
            }
            for item in NiftiArtifact.objects.filter(series_id__in=series_ids).order_by("role")
        ]
        result = AIAnalysisResult.objects.filter(analysis=analysis).first()
        masks = [] if result is None else [
            {
                "artifact_id": str(item.id),
                "type": item.artifact_type,
                "url": f"/api/v1/ai-result-artifacts/{item.id}/content",
            }
            for item in AIResultArtifact.objects.filter(result=result, artifact_type="NIFTI_MASK")
        ]
        return Response({"analysis_id": str(analysis.id), "inputs": inputs, "masks": masks})


class ResultArtifactContentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, artifact_id):
        artifact = AIResultArtifact.objects.select_related("result__analysis").filter(pk=artifact_id).first()
        if artifact is None or not _can_read_analysis(request, artifact.result.analysis):
            raise Http404
        return open_gcs_uri(artifact.uri)


class AIResultReviewCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    def _result(self, request, result_id):
        result = AIAnalysisResult.objects.select_related("analysis").filter(pk=result_id).first()
        if result is None or not _can_read_analysis(request, result.analysis):
            raise Http404
        return result

    def get(self, request, result_id):
        result = self._result(request, result_id)
        rows = AIResultReview.objects.filter(result=result).order_by("-reviewed_at")
        return Response({"result_id": str(result.id), "reviews": [self._payload(row) for row in rows]})

    def post(self, request, result_id):
        result = self._result(request, result_id)
        decision = request.data.get("decision")
        comment = str(request.data.get("comment", "")).strip()
        if decision not in {"ACCEPT", "MODIFY", "REJECT"} or not comment:
            raise serializers.ValidationError({"detail": "decision and comment are required."})
        review = AIResultReview.objects.create(
            result=result, reviewer=request.user, decision=decision, comment=comment,
            corrected_findings=request.data.get("corrected_findings") or {}, reviewed_at=timezone.now(),
        )
        return Response(self._payload(review), status=status.HTTP_201_CREATED)

    @staticmethod
    def _payload(review):
        return {
            "review_id": str(review.id), "result_id": str(review.result_id),
            "decision": review.decision, "comment": review.comment,
            "corrected_findings": review.corrected_findings,
            "reviewer_id": str(review.reviewer_id), "reviewed_at": review.reviewed_at,
        }
