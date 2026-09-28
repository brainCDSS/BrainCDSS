"""Local-only API using existing analysis tables and synthetic references."""

from kombu.exceptions import OperationalError
from django.conf import settings
from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisResult,
    AIAnalysisStatusHistory,
    AIModelConfigVersion,
    ModelVersion,
)
from apps.ai_analysis.services.inference import (
    create_queued_analysis,
    transition_analysis,
)
from apps.ai_analysis.tasks.mock_inference import run_mock_analysis_inference
from apps.imaging.models import ImagingStudy


class DevelopmentAnalysisRequest(serializers.Serializer):
    study_id = serializers.UUIDField()
    model_version_id = serializers.UUIDField()
    model_config_version_id = serializers.UUIDField()
    requested_by_id = serializers.UUIDField()
    analysis_type = serializers.CharField(max_length=64, default="MOCK_INFERENCE")
    priority = serializers.ChoiceField(
        choices=["NORMAL", "HIGH", "CRITICAL"],
        default="NORMAL",
    )
    outcome = serializers.ChoiceField(
        choices=["success", "failure"],
        default="success",
        write_only=True,
    )

    def validate(self, attrs):
        model_version = ModelVersion.objects.filter(
            pk=attrs["model_version_id"],
            is_active=True,
        ).first()
        if model_version is None:
            raise serializers.ValidationError({
                "model_version_id": "Active model version not found."
            })
        model_config = AIModelConfigVersion.objects.filter(
            pk=attrs["model_config_version_id"],
            model_version=model_version,
            is_active=True,
        ).first()
        if model_config is None:
            raise serializers.ValidationError({
                "model_config_version_id": (
                    "Active config for the selected model version not found."
                )
            })
        try:
            attrs["study"] = ImagingStudy.objects.get(
                pk=attrs["study_id"],
                status="AVAILABLE",
            )
            attrs["requested_by"] = User.objects.get(
                pk=attrs["requested_by_id"],
                is_active=True,
            )
        except (ImagingStudy.DoesNotExist, User.DoesNotExist) as exc:
            raise serializers.ValidationError(
                "Available study and active requester are required."
            ) from exc
        attrs["model_version"] = model_version
        attrs["model_config_version"] = model_config
        return attrs


def analysis_payload(analysis):
    history = AIAnalysisStatusHistory.objects.filter(
        analysis=analysis,
    ).order_by("occurred_at")
    result = AIAnalysisResult.objects.filter(analysis=analysis).first()
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "stage": analysis.stage,
        "analysis_type": analysis.analysis_type,
        "failure_code": analysis.failure_code,
        "attempt_count": analysis.attempt_count,
        "history": [
            {
                "previous_status": item.previous_status,
                "status": item.status,
                "stage": item.stage,
                "reason_code": item.reason_code,
                "occurred_at": item.occurred_at.isoformat(),
            }
            for item in history
        ],
        "result": result.structured_findings if result else None,
    }


class DevelopmentAnalysisView(APIView):
    authentication_classes = []
    permission_classes = []

    def initial(self, request, *args, **kwargs):
        if not settings.AI_INFERENCE_DEVELOPMENT_ENABLED:
            raise Http404
        super().initial(request, *args, **kwargs)

    def post(self, request, analysis_id=None):
        if analysis_id is not None:
            return Response(status=405)
        serializer = DevelopmentAnalysisRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        analysis = create_queued_analysis(
            study=values["study"],
            model_version=values["model_version"],
            model_config_version=values["model_config_version"],
            requested_by=values["requested_by"],
            analysis_type=values["analysis_type"],
            priority=values["priority"],
        )
        try:
            run_mock_analysis_inference.apply_async(
                args=[str(analysis.id), values["outcome"]],
                retry=False,
            )
        except (OperationalError, OSError):
            transition_analysis(
                analysis,
                status="FAILED",
                stage="VALIDATING",
                reason_code="BROKER_UNAVAILABLE",
            )
            return Response(analysis_payload(analysis), status=503)
        return Response(analysis_payload(analysis), status=202)

    def get(self, request, analysis_id=None):
        if analysis_id is None:
            return Response(status=405)
        try:
            analysis = AIAnalysis.objects.get(pk=analysis_id)
        except AIAnalysis.DoesNotExist as exc:
            raise Http404 from exc
        return Response(analysis_payload(analysis))
