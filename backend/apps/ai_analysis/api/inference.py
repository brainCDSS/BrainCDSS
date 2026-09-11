"""Authenticated API for creating and reading real AI analyses."""

from django.http import Http404
from kombu.exceptions import OperationalError
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.models import RolePermission
from apps.ai_analysis.models import AIAnalysis, AIAnalysisInputSeries, AIAnalysisResult, AIModelConfigVersion, AIResultArtifact, AIRoutingConfigVersion, ModelVersion
from apps.ai_analysis.api.generated_real_149 import ContractView000, SPECS
from apps.ai_analysis.services.inference import create_queued_analysis, transition_analysis
from apps.ai_analysis.tasks.inference import ROLE_ORDER, run_analysis_inference
from apps.common.remaining149_runtime import execute_contract
from apps.imaging.models import ImagingStudy, NiftiArtifact
from apps.imaging.services.nifti import open_gcs_uri


CLINICAL_AI_ROLES = {"NEUROLOGIST", "NEUROSURGEON", "RADIOLOGY"}
AI_ANALYSIS_LIST_SPEC = next(spec for spec in SPECS if spec["api_id"] == "API-AI-002")


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
    """Keep the generated GET worklist while replacing POST with real inference."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, "role", None)
        role_code = getattr(role, "code", None)

        if role_code in CLINICAL_AI_ROLES:
            clinical_spec = {**AI_ANALYSIS_LIST_SPEC, "permission": None}
            return execute_contract(request, clinical_spec)

        if role_code == "SYSTEM_ADMIN":
            has_job_view = RolePermission.objects.filter(
                role=role,
                permission__code="ai.job.view",
            ).exists()
            if has_job_view:
                return execute_contract(request, AI_ANALYSIS_LIST_SPEC)

        raise PermissionDenied({
            "code": "AI_ANALYSIS_LIST_FORBIDDEN",
            "detail": "The current role cannot view AI analysis jobs.",
        })
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
