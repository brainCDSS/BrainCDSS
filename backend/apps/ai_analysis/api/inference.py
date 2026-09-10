"""Authenticated API for creating and reading real AI analyses."""

from django.http import Http404
from kombu.exceptions import OperationalError
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_analysis.models import AIAnalysis, AIAnalysisResult, AIModelConfigVersion, ModelVersion
from apps.ai_analysis.api.generated_real_149 import ContractView000
from apps.ai_analysis.services.inference import create_queued_analysis, transition_analysis
from apps.ai_analysis.tasks.inference import ROLE_ORDER, run_analysis_inference
from apps.imaging.models import ImagingStudy


class InputArtifactSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["CT", "DWI", "ADC", "MRA"])
    uri = serializers.RegexField(r"^gs://[^/]+/.+", max_length=1024)
    size_bytes = serializers.IntegerField(min_value=1)
    sha256 = serializers.RegexField(r"^[a-f0-9]{64}$")


class AnalysisCreateSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    model_version_id = serializers.UUIDField()
    model_config_version_id = serializers.UUIDField()
    analysis_type = serializers.ChoiceField(choices=list(ROLE_ORDER))
    priority = serializers.ChoiceField(choices=["NORMAL", "HIGH", "CRITICAL"], default="NORMAL")
    inputs = InputArtifactSerializer(many=True, min_length=1, max_length=2)

    def validate(self, attrs):
        version = ModelVersion.objects.filter(
            pk=attrs["model_version_id"], is_active=True, validation_status="APPROVED"
        ).select_related("model").first()
        if version is None:
            raise serializers.ValidationError({"model_version_id": "Approved model version not found."})
        config = AIModelConfigVersion.objects.filter(
            pk=attrs["model_config_version_id"], model_version=version, is_active=True
        ).first()
        if config is None:
            raise serializers.ValidationError({"model_config_version_id": "Active model config not found."})
        study = ImagingStudy.objects.filter(pk=attrs["study_id"], status="AVAILABLE").first()
        if study is None:
            raise serializers.ValidationError({"study_id": "Available study not found."})
        roles = [item["role"] for item in attrs["inputs"]]
        expected = list(ROLE_ORDER[attrs["analysis_type"]])
        if roles != expected:
            raise serializers.ValidationError({"inputs": f"roles must be {expected} in order"})
        attrs.update(model_version=version, model_config_version=config, study=study)
        return attrs


def analysis_payload(analysis):
    result = AIAnalysisResult.objects.filter(analysis=analysis).first()
    return {
        "analysis_id": str(analysis.id),
        "analysis_type": analysis.analysis_type,
        "status": analysis.status,
        "stage": analysis.stage,
        "attempt_count": analysis.attempt_count,
        "failure_code": analysis.failure_code,
        "trace_id": analysis.trace,
        "result": result.structured_findings if result else None,
    }


class AnalysisCollectionView(ContractView000):
    """Keep the generated GET worklist while replacing POST with real inference."""

    permission_classes = [IsAuthenticated]

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
