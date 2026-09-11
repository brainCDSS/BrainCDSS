from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.medication_safety.api.permissions import (
    MedicationSafetyCheckPermission,
)
from apps.prescriptions.services.prescription_finalize import (
    PrescriptionFinalizeError,
    finalize_prescription,
)


class PrescriptionFinalizeView(APIView):
    """
    API-RX-004
    처방 최종 확정 API

    Body 예:
    {
        "overrides": [
            {
                "alert_type": "DDI",
                "rule_type": "DDI",
                "rule_id": "...uuid...",
                "reason": "임상적 필요에 따른 처방"
            }
        ]
    }
    """

    permission_classes = [
        MedicationSafetyCheckPermission,
    ]

    @extend_schema(
        operation_id="api_rx_004",
        summary="처방 최종 확정",
        description=(
            "Safety 재검사 후 처방을 FINAL로 "
            "확정하고 Override, Schedule, "
            "AuditLog, OutboxEvent를 "
            "동일 트랜잭션에서 처리한다."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "overrides": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "alert_type": {
                                    "type": "string"
                                },
                                "rule_type": {
                                    "type": "string"
                                },
                                "rule_id": {
                                    "type": "string",
                                    "format": "uuid",
                                },
                                "reason": {
                                    "type": "string"
                                },
                            },
                        },
                    }
                },
            }
        },
        responses={
            200: OpenApiResponse(
                description="Prescription FINAL",
            ),
            400: OpenApiResponse(
                description=(
                    "PRESCRIPTION_EMPTY / "
                    "PRESCRIPTION_FINALIZE_INVALID"
                ),
            ),
            403: OpenApiResponse(
                description=(
                    "PRESCRIPTION_FINALIZE_FORBIDDEN / "
                    "FORBIDDEN_PERMISSION"
                ),
            ),
            404: OpenApiResponse(
                description="PRESCRIPTION_NOT_FOUND",
            ),
            409: OpenApiResponse(
                description=(
                    "PRESCRIPTION_INVALID_STATE / "
                    "MEDICATION_SAFETY_BLOCKED"
                ),
            ),
            422: OpenApiResponse(
                description="OVERRIDE_REASON_REQUIRED",
            ),
            503: OpenApiResponse(
                description=(
                    "MEDICATION_SAFETY_UNAVAILABLE"
                ),
            ),
        },
        tags=["prescriptions"],
    )
    def post(
        self,
        request,
        prescription_id,
    ):
        body = request.data

        if body is None:
            body = {}

        if not isinstance(body, dict):
            raise ContractAPIException(
                "PRESCRIPTION_FINALIZE_INVALID",
                "Request body must be an object.",
                400,
            )

        overrides = body.get(
            "overrides",
            [],
        )

        try:
            result = finalize_prescription(
                prescription_id=prescription_id,
                actor_user=request.user,
                overrides=overrides,
                request=request,
            )

        except PrescriptionFinalizeError as exc:
            raise ContractAPIException(
                exc.code,
                exc.detail,
                exc.status_code,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
