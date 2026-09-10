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
from apps.accounts.api.permissions import (
    SystemAdminPermission,
)
from apps.medication_safety.api.dur_serializers import (
    DurSyncRequestSerializer,
    DurSyncResponseSerializer,
)
from apps.medication_safety.services.dur_admin import (
    DurSyncInProgress,
    enqueue_dur_sync,
)


class DurSyncView(APIView):
    permission_classes = [
        SystemAdminPermission,
    ]

    required_permission_code = "dur.sync"

    @extend_schema(
        operation_id="api_dur_001",
        summary="DUR 수동 동기화 Trigger",
        description=(
            "SYSTEM_ADMIN 전용 DUR 비동기 동기화. "
            "현재 INTERACTION 및 DOSE를 지원한다."
        ),
        request=DurSyncRequestSerializer,
        responses={
            202: DurSyncResponseSerializer,
            400: OpenApiResponse(
                description=(
                    "DUR_SYNC_INPUT_INVALID"
                ),
            ),
            403: OpenApiResponse(
                description=(
                    "FORBIDDEN_ROLE / "
                    "missing dur.sync permission"
                ),
            ),
            409: OpenApiResponse(
                description=(
                    "DUR_SYNC_IN_PROGRESS"
                ),
            ),
            502: OpenApiResponse(
                description="DUR_SYNC_FAILED",
            ),
        },
        tags=["medication_safety"],
    )
    def post(self, request):
        serializer = (
            DurSyncRequestSerializer(
                data=request.data
            )
        )

        if not serializer.is_valid():
            raise ContractAPIException(
                "DUR_SYNC_INPUT_INVALID",
                str(serializer.errors),
                400,
            )

        sync_types = (
            serializer.validated_data[
                "sync_types"
            ]
        )

        try:
            payload = enqueue_dur_sync(
                request=request,
                sync_types=sync_types,
            )

        except DurSyncInProgress as exc:
            raise ContractAPIException(
                "DUR_SYNC_IN_PROGRESS",
                (
                    "Another DUR synchronization "
                    f"is running. task_id={exc.task_id}"
                ),
                409,
            )

        except Exception as exc:
            raise ContractAPIException(
                "DUR_SYNC_FAILED",
                (
                    "DUR synchronization could "
                    "not be queued. "
                    f"{type(exc).__name__}"
                ),
                502,
            )

        return Response(
            payload,
            status=status.HTTP_202_ACCEPTED,
        )
