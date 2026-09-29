"""System-admin model routing operations backed by existing AI tables."""

from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request as UrlRequest, urlopen

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode, User
from apps.ai_analysis.models import AIModel, AIModelConfigVersion, AIRoutingConfigVersion, ModelVersion
from apps.ai_analysis.services.mlflow_registry import MLflowRegistryError, fetch_mlflow_cloud_run_id_token
from apps.ai_analysis.services.mlflow_sync import MLflowModelVersionSyncService
from apps.ai_analysis.services.model_validation import MLModelVersionValidationService
from apps.audit.services.audit_event import record_audit_event


def _require_system_admin(request):
    if getattr(getattr(request.user, "role", None), "code", None) != "SYSTEM_ADMIN":
        raise PermissionDenied({"code": "SYSTEM_ADMIN_REQUIRED"})


_MLFLOW_PROXY_COOKIE = "brainon_mlflow_proxy"
_MLFLOW_PROXY_SALT = "brainon.mlflow.proxy.v1"
_MLFLOW_PROXY_PREFIX = "/api/v1/admin/ml/mlflow/"
_MLFLOW_PROXY_SESSION_SECONDS = 15 * 60
_MLFLOW_PROXY_RESPONSE_HEADERS = {
    "cache-control", "content-disposition", "content-language", "content-type",
    "etag", "last-modified", "vary",
}
_MLFLOW_READ_ONLY_POST_PATHS = {
    "search",
    "search-datasets",
    "get-experiment",
}


def _mlflow_proxy_session(user: User) -> str:
    return signing.dumps({"user_id": str(user.id)}, salt=_MLFLOW_PROXY_SALT, compress=True)


def _mlflow_proxy_user(request) -> User | None:
    token = request.COOKIES.get(_MLFLOW_PROXY_COOKIE, "")
    if not token:
        return None
    try:
        payload = signing.loads(token, salt=_MLFLOW_PROXY_SALT, max_age=_MLFLOW_PROXY_SESSION_SECONDS)
    except signing.BadSignature:
        return None
    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    if not user_id:
        return None
    return (
        User.objects.select_related("role")
        .filter(pk=user_id, is_active=True, role__code=RoleCode.SYSTEM_ADMIN, role__is_active=True)
        .first()
    )


def _mlflow_proxy_url(proxy_path: str, query_string: str) -> str:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "").strip().rstrip("/")
    if not tracking_uri:
        raise MLflowRegistryError("MLFLOW_TRACKING_URI is not configured")
    safe_path = quote(proxy_path.lstrip("/"), safe="/@:+,;=-._~")
    url = f"{tracking_uri}/{safe_path}"
    return f"{url}?{query_string}" if query_string else url


def _proxy_response_headers(upstream_headers, response) -> None:
    for name, value in upstream_headers.items():
        if name.lower() in _MLFLOW_PROXY_RESPONSE_HEADERS:
            response[name] = value


def _is_read_only_mlflow_post(request, proxy_path: str) -> bool:
    """Allow MLflow's query-style POSTs while rejecting state changes."""

    normalized_path = proxy_path.strip("/").lower()
    if normalized_path.endswith("graphql"):
        try:
            payload = json.loads(request.body)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        query = payload.get("query") if isinstance(payload, dict) else None
        if not isinstance(query, str):
            return False
        return bool(
            re.match(r"^\s*(query\b|\{)", query, flags=re.IGNORECASE)
            and not re.search(r"\bmutation\b", query, flags=re.IGNORECASE)
        )
    return (
        normalized_path in _MLFLOW_READ_ONLY_POST_PATHS
        or normalized_path.endswith("/search")
        or normalized_path.endswith("/search-datasets")
    )


class MLflowProxySessionView(APIView):
    """Issue a short-lived, HttpOnly session for the browser-only MLflow proxy."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_system_admin(request)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.set_cookie(
            _MLFLOW_PROXY_COOKIE,
            _mlflow_proxy_session(request.user),
            max_age=_MLFLOW_PROXY_SESSION_SECONDS,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Strict",
            path=_MLFLOW_PROXY_PREFIX,
        )
        response["Cache-Control"] = "no-store"
        record_audit_event(
            source_service="backend.ai_analysis",
            action="MLFLOW_UI_SESSION_OPENED",
            resource_type="MLflowUI",
            resource_id=request.user.id,
            outcome="SUCCESS",
            request=request,
            reason="SYSTEM_ADMIN MLflow read-only UI access",
        )
        return response


class MLflowReadOnlyProxyView(APIView):
    """Serve private MLflow read-only pages to active BrainOn system administrators."""

    permission_classes = [AllowAny]

    def _forward(self, request, proxy_path: str, *, method: str, data: bytes | None = None):
        if _mlflow_proxy_user(request) is None:
            return Response({"code": "SYSTEM_ADMIN_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
        try:
            headers = {
                "Authorization": f"Bearer {fetch_mlflow_cloud_run_id_token()}",
                "User-Agent": "BrainOn-MLflow-ReadOnly-Proxy/1.0",
            }
            if data is not None:
                headers["Content-Type"] = request.content_type or "application/json"
            upstream_request = UrlRequest(
                _mlflow_proxy_url(proxy_path, request.META.get("QUERY_STRING", "")),
                data=data,
                headers=headers,
                method=method,
            )
            upstream = urlopen(
                upstream_request,
                timeout=int(os.getenv("MLFLOW_UI_PROXY_TIMEOUT_SECONDS", "30")),
            )
        except HTTPError as error:
            response = HttpResponse(error.read(), status=error.code)
            _proxy_response_headers(error.headers, response)
            return response
        except (MLflowRegistryError, URLError, OSError, ValueError):
            return Response({"code": "MLFLOW_UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        def body_iterator():
            try:
                while chunk := upstream.read(64 * 1024):
                    yield chunk
            finally:
                upstream.close()

        response = StreamingHttpResponse(
            body_iterator(), status=upstream.status,
            content_type=upstream.headers.get("Content-Type"),
        )
        _proxy_response_headers(upstream.headers, response)
        response["Cache-Control"] = "no-store"
        return response

    def get(self, request, proxy_path=""):
        return self._forward(request, proxy_path, method="GET")

    def post(self, request, proxy_path=""):
        if not _is_read_only_mlflow_post(request, proxy_path):
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return self._forward(request, proxy_path, method="POST", data=request.body)

    put = post
    patch = post
    delete = post


def _model_version_payload(version):
    metrics = version.performance_metrics or {}
    mlflow_metadata = metrics.get("_mlflow", {})
    if not isinstance(mlflow_metadata, dict):
        mlflow_metadata = {}
    return {
        "version_id": str(version.id),
        "model_id": str(version.model_id),
        "model_code": version.model.code,
        "model_name": version.model.display_name,
        "version": version.version,
        "mlflow_registered_model_name": version.mlflow_registered_model_name,
        "mlflow_model_version": version.mlflow_model_version,
        "mlflow_run_id": version.mlflow_run,
        "artifact_uri": version.artifact_uri,
        "validation_status": version.validation_status,
        "is_active": version.is_active,
        "performance_metrics": metrics,
        "experiment_id": mlflow_metadata.get("experiment_id", ""),
        "model_bundle_uri": mlflow_metadata.get("model_bundle_uri", ""),
        "manifest_uri": mlflow_metadata.get("manifest_uri", ""),
        "checkpoint_uri": mlflow_metadata.get("checkpoint_uri", ""),
        "created_at": version.created_at.isoformat(),
        "updated_at": version.updated_at.isoformat(),
    }


def _routing_payload(routing):
    target = routing.target_model_version
    return {
        "routing_id": str(routing.id),
        "version": routing.version,
        "modality": routing.modality,
        "analysis_type": routing.analysis_type,
        "is_active": routing.is_active,
        "created_at": routing.created_at.isoformat(),
        "target_model_version": (
            _model_version_payload(target) if target is not None else None
        ),
    }


class RoutingCreateSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=32)
    modality = serializers.ChoiceField(choices=["CT", "MR", "MRA"])
    analysis_type = serializers.CharField(max_length=64)
    target_model_version_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=500)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    confirmation = serializers.BooleanField()


class ValidationRequestSerializer(ReasonSerializer):
    threshold = serializers.FloatField(min_value=0, max_value=1, required=False)


class MLModelOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_system_admin(request)
        models = AIModel.objects.order_by("code")
        versions = ModelVersion.objects.select_related("model").order_by("model__code", "-created_at")
        routings = AIRoutingConfigVersion.objects.select_related(
            "target_model_version__model"
        ).order_by("modality", "analysis_type", "-created_at")
        return Response({
            "models": [
                {
                    "model_id": str(model.id),
                    "code": model.code,
                    "display_name": model.display_name,
                    "task_type": model.task_type,
                    "disease_scope": model.disease_scope,
                    "supported_modalities": model.supported_modalities,
                    "is_enabled": model.is_enabled,
                }
                for model in models
            ],
            "versions": [_model_version_payload(version) for version in versions],
            "routing_configs": [_routing_payload(routing) for routing in routings],
        })


class MLflowModelVersionSyncView(APIView):
    """Import Registry metadata without changing model approval or routing."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_system_admin(request)
        try:
            result = MLflowModelVersionSyncService().sync(request=request)
        except MLflowRegistryError:
            return Response(
                {
                    "code": "MLFLOW_UNAVAILABLE",
                    "detail": "MLflow Registry synchronization is unavailable.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result.as_dict())


class MLModelVersionValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id):
        _require_system_admin(request)
        data = ValidationRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not data.validated_data["confirmation"]:
            raise ValidationError({"confirmation": "true is required."})

        version = ModelVersion.objects.select_related("model").filter(pk=version_id).first()
        if version is None:
            raise NotFound({"code": "MODEL_VERSION_NOT_FOUND"})
        if version.validation_status != "DRAFT":
            raise ValidationError({"code": "MODEL_VALIDATE_INVALID_STATE"})

        validation = MLModelVersionValidationService().validate(
            version,
            threshold_override=data.validated_data.get("threshold"),
        )
        if not validation.passed:
            return Response(
                {"code": "MODEL_VALIDATION_FAILED", **validation.as_dict()},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        with transaction.atomic():
            locked = ModelVersion.objects.select_for_update().select_related("model").get(pk=version_id)
            if locked.validation_status != "DRAFT":
                raise ValidationError({"code": "MODEL_VALIDATE_INVALID_STATE"})
            before = _model_version_payload(locked)
            locked.input_contract = validation.input_contract
            locked.output_contract = validation.output_contract
            locked.preprocessing_config = validation.preprocessing_config
            locked.validation_status = "VALIDATED"
            locked.updated_at = timezone.now()
            locked.save(update_fields=[
                "input_contract", "output_contract", "preprocessing_config",
                "validation_status", "updated_at",
            ])
            AIModelConfigVersion.objects.filter(model_version=locked, is_active=True).update(is_active=False)
            AIModelConfigVersion.objects.create(
                model_version=locked,
                config_version=f"mlflow-{locked.mlflow_model_version}",
                threshold_config=validation.threshold_config,
                is_active=True,
                created_at=timezone.now(),
            )
            record_audit_event(
                source_service="backend.ai_analysis",
                action="AI_MODEL_VERSION_VALIDATED",
                resource_type="ModelVersion",
                resource_id=locked.id,
                outcome="SUCCESS",
                request=request,
                reason=data.validated_data["reason"],
                before_json=before,
                after_json={**_model_version_payload(locked), "checks": validation.as_dict()["checks"]},
            )
        return Response({**_model_version_payload(locked), **validation.as_dict()})


class MLModelVersionApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id):
        _require_system_admin(request)
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not data.validated_data["confirmation"]:
            raise ValidationError({"confirmation": "true is required."})

        with transaction.atomic():
            version = ModelVersion.objects.select_for_update().select_related("model").filter(pk=version_id).first()
            if version is None:
                raise NotFound({"code": "MODEL_VERSION_NOT_FOUND"})
            if version.validation_status != "VALIDATED":
                raise ValidationError({"code": "MODEL_APPROVE_INVALID_STATE"})
            if not AIModelConfigVersion.objects.filter(model_version=version, is_active=True).exists():
                raise ValidationError({"code": "MODEL_CONFIG_NOT_ACTIVE"})
            before = _model_version_payload(version)
            version.validation_status = "APPROVED"
            version.updated_at = timezone.now()
            version.save(update_fields=["validation_status", "updated_at"])
            record_audit_event(
                source_service="backend.ai_analysis",
                action="AI_MODEL_VERSION_APPROVED",
                resource_type="ModelVersion",
                resource_id=version.id,
                outcome="SUCCESS",
                request=request,
                reason=data.validated_data["reason"],
                before_json=before,
                after_json=_model_version_payload(version),
            )
        return Response(_model_version_payload(version))


class MLModelVersionRetireView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, version_id):
        _require_system_admin(request)
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not data.validated_data["confirmation"]:
            raise ValidationError({"confirmation": "true is required."})

        with transaction.atomic():
            version = ModelVersion.objects.select_for_update().select_related("model").filter(pk=version_id).first()
            if version is None:
                raise NotFound({"code": "MODEL_VERSION_NOT_FOUND"})
            if version.is_active or AIRoutingConfigVersion.objects.filter(target_model_version=version, is_active=True).exists():
                raise ValidationError({"code": "MODEL_VERSION_ACTIVE"})
            before = _model_version_payload(version)
            version.validation_status = "RETIRED"
            version.updated_at = timezone.now()
            version.save(update_fields=["validation_status", "updated_at"])
            record_audit_event(
                source_service="backend.ai_analysis",
                action="AI_MODEL_VERSION_RETIRED",
                resource_type="ModelVersion",
                resource_id=version.id,
                outcome="SUCCESS",
                request=request,
                reason=data.validated_data["reason"],
                before_json=before,
                after_json=_model_version_payload(version),
            )
        return Response(_model_version_payload(version))


class MLRoutingCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_system_admin(request)
        data = RoutingCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        with transaction.atomic():
            version = ModelVersion.objects.select_for_update().select_related("model").filter(
                pk=values["target_model_version_id"], validation_status="APPROVED"
            ).first()
            if version is None:
                raise ValidationError({"target_model_version_id": "An approved model version is required."})
            supported_modalities = set(version.model.supported_modalities or [])
            mra_compatible = (
                values["modality"] == "MRA"
                and "MR" in supported_modalities
                and (
                    version.model.disease_scope == "ANEURYSM"
                    or "MRA" in version.model.display_name.upper()
                )
            )
            if values["modality"] not in supported_modalities and not mra_compatible:
                raise ValidationError({"modality": "The target model does not support this modality."})
            if AIRoutingConfigVersion.objects.filter(version=values["version"]).exists():
                raise ValidationError({"version": "Routing version already exists."})
            routing = AIRoutingConfigVersion.objects.create(
                version=values["version"],
                modality=values["modality"],
                analysis_type=values["analysis_type"],
                target_model_version=version,
                is_active=False,
                created_at=timezone.now(),
            )
            record_audit_event(
                source_service="backend.ai_analysis",
                action="AI_ROUTING_CREATED",
                resource_type="AIRoutingConfigVersion",
                resource_id=routing.id,
                outcome="SUCCESS",
                request=request,
                reason=values["reason"],
                after_json=_routing_payload(routing),
            )
        return Response(_routing_payload(routing), status=status.HTTP_201_CREATED)


class MLRoutingActivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, routing_id):
        _require_system_admin(request)
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not data.validated_data["confirmation"]:
            raise ValidationError({"confirmation": "true is required."})
        with transaction.atomic():
            # nullable FK까지 함께 잠그지 않고 라우팅 행만 잠근다.
            routing = (
                AIRoutingConfigVersion.objects
                .select_for_update()
                .filter(pk=routing_id)
                .first()
            )

            if routing is None:
                raise NotFound({"code": "ROUTING_NOT_FOUND"})

            # 대상 모델은 별도 쿼리로 조회한다.
            target = (
                ModelVersion.objects
                .select_related("model")
                .filter(pk=routing.target_model_version_id)
                .first()
            )
            if target is None or target.validation_status != "APPROVED":
                raise ValidationError({"code": "TARGET_MODEL_NOT_APPROVED"})
            if not AIModelConfigVersion.objects.filter(model_version=target, is_active=True).exists():
                raise ValidationError({"code": "MODEL_CONFIG_NOT_ACTIVE"})
            previous = AIRoutingConfigVersion.objects.select_for_update().filter(
                modality=routing.modality,
                analysis_type=routing.analysis_type,
                is_active=True,
            ).exclude(pk=routing.pk)
            previous_ids = list(previous.values_list("id", flat=True))
            previous.update(is_active=False)
            routing.is_active = True
            routing.save(update_fields=["is_active"])
            if not target.is_active:
                target.is_active = True
                target.updated_at = timezone.now()
                target.save(update_fields=["is_active", "updated_at"])
            record_audit_event(
                source_service="backend.ai_analysis",
                action="AI_ROUTING_ACTIVATED",
                resource_type="AIRoutingConfigVersion",
                resource_id=routing.id,
                outcome="SUCCESS",
                request=request,
                reason=data.validated_data["reason"],
                after_json={
                    "routing": _routing_payload(routing),
                    "previous_active_routing_ids": [str(item) for item in previous_ids],
                },
            )
        return Response(_routing_payload(routing))
