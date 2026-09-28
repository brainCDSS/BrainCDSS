from django.db import transaction
from django.db.models import Q
from django.utils import timezone

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
from apps.notifications.api.fcm_serializers import (
    FCMTokenRegisterSerializer,
)
from apps.notifications.api.permissions import (
    FCMManagePermission,
)
from apps.notifications.models import (
    FCMDeviceToken,
)


def _response_payload(
    instance: FCMDeviceToken,
) -> dict:
    return {
        "token_id": str(instance.id),
        "device_id": instance.device,
        "platform": instance.platform,
        "is_active": instance.is_active,
        "last_seen_at": (
            instance.last_seen_at.isoformat()
            if instance.last_seen_at
            else None
        ),
    }


class FCMTokenCollectionView(APIView):
    permission_classes = [
        FCMManagePermission,
    ]

    @extend_schema(
        operation_id="api_fcm_001",
        summary="FCM Token 등록/갱신",
        description=(
            "현재 로그인 사용자의 FCM device token을 "
            "등록하거나 갱신한다."
        ),
        request=FCMTokenRegisterSerializer,
        responses={
            200: OpenApiResponse(
                description="Existing token updated.",
            ),
            201: OpenApiResponse(
                description="New token created.",
            ),
            400: OpenApiResponse(
                description=(
                    "FCM_TOKEN_INVALID / "
                    "VALIDATION_ERROR"
                ),
            ),
            403: OpenApiResponse(
                description=(
                    "FORBIDDEN_ROLE / "
                    "FORBIDDEN_PERMISSION"
                ),
            ),
        },
        tags=["notifications"],
    )
    def post(
        self,
        request,
    ):
        serializer = (
            FCMTokenRegisterSerializer(
                data=request.data,
            )
        )

        if not serializer.is_valid():
            raise ContractAPIException(
                "FCM_TOKEN_INVALID",
                str(serializer.errors),
                400,
            )

        device_id = (
            serializer.validated_data[
                "device_id"
            ]
        )

        platform = (
            serializer.validated_data[
                "platform"
            ]
        )

        token = (
            serializer.validated_data[
                "token"
            ]
        )

        now = timezone.now()

        with transaction.atomic():
            matches = list(
                FCMDeviceToken.objects
                .select_for_update()
                .filter(
                    Q(device=device_id)
                    | Q(token=token)
                )
            )

            device_row = next(
                (
                    row
                    for row in matches
                    if row.device == device_id
                ),
                None,
            )

            token_row = next(
                (
                    row
                    for row in matches
                    if row.token == token
                ),
                None,
            )

            created = False

            if device_row is not None:
                target = device_row

                if (
                    token_row is not None
                    and token_row.pk
                    != device_row.pk
                ):
                    token_row.delete()

                target.user = request.user
                target.platform = platform
                target.token = token
                target.is_active = True
                target.last_seen_at = now
                target.updated_at = now

                target.save(
                    update_fields=[
                        "user",
                        "platform",
                        "token",
                        "is_active",
                        "last_seen_at",
                        "updated_at",
                    ]
                )

            elif token_row is not None:
                target = token_row

                target.user = request.user
                target.device = device_id
                target.platform = platform
                target.is_active = True
                target.last_seen_at = now
                target.updated_at = now

                target.save(
                    update_fields=[
                        "user",
                        "device",
                        "platform",
                        "is_active",
                        "last_seen_at",
                        "updated_at",
                    ]
                )

            else:
                target = FCMDeviceToken.objects.create(
                    user=request.user,
                    device=device_id,
                    platform=platform,
                    token=token,
                    is_active=True,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )

                created = True

        return Response(
            _response_payload(target),
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )


class FCMTokenDetailView(APIView):
    permission_classes = [
        FCMManagePermission,
    ]

    @extend_schema(
        operation_id="api_fcm_002",
        summary="FCM Token 비활성화",
        description=(
            "현재 로그인 사용자가 소유한 "
            "FCM token을 비활성화한다."
        ),
        responses={
            204: OpenApiResponse(
                description="Token deactivated.",
            ),
            403: OpenApiResponse(
                description=(
                    "FORBIDDEN_ROLE / "
                    "FORBIDDEN_PERMISSION"
                ),
            ),
            404: OpenApiResponse(
                description=(
                    "FCM_TOKEN_NOT_FOUND"
                ),
            ),
        },
        tags=["notifications"],
    )
    def delete(
        self,
        request,
        token_id,
    ):
        now = timezone.now()

        with transaction.atomic():
            token = (
                FCMDeviceToken.objects
                .select_for_update()
                .filter(
                    pk=token_id,
                    user=request.user,
                )
                .first()
            )

            if token is None:
                raise ContractAPIException(
                    "FCM_TOKEN_NOT_FOUND",
                    "FCM token was not found.",
                    404,
                )

            if token.is_active:
                token.is_active = False
                token.updated_at = now

                token.save(
                    update_fields=[
                        "is_active",
                        "updated_at",
                    ]
                )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
