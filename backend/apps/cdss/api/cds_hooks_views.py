from drf_spectacular.types import (
    OpenApiTypes,
)
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.response import (
    Response,
)
from rest_framework.views import (
    APIView,
)

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.cdss.api.cds_service_authentication import (
    CDSServiceJWTAuthentication,
    RequiredCDSServiceScopePermission,
)
from apps.cdss.services.medication_safety_cds_hooks import (
    CDSHookError,
    evaluate_medication_safety_cds_hook,
)


CDS_SERVICES = [
    {
        "hook": "order-select",
        "title": (
            "BrainOn Medication Safety "
            "Order Select"
        ),
        "description": (
            "약 선택 직후 가능한 DUR 및 "
            "약물안전성 검사를 수행합니다."
        ),
        "id": (
            "medication-safety-order-select"
        ),
        "usageRequirements": (
            "Service JWT scope "
            "cds.medication-safety.invoke "
            "required."
        ),
    },
    {
        "hook": "order-sign",
        "title": (
            "BrainOn Medication Safety "
            "Order Sign"
        ),
        "description": (
            "처방 서명 직전 7종 "
            "약물안전성 검사를 수행합니다."
        ),
        "id": (
            "medication-safety-order-sign"
        ),
        "usageRequirements": (
            "Service JWT scope "
            "cds.medication-safety.invoke "
            "required."
        ),
    },
    {
        "hook": "patient-view",
        "title": (
            "BrainOn Stroke "
            "Patient View"
        ),
        "description": (
            "뇌졸중 환자 진료 Context의 "
            "CDSS Card를 제공합니다."
        ),
        "id": "stroke-patient-view",
        "usageRequirements": (
            "Service JWT scope "
            "cds.stroke.invoke required."
        ),
    },
]


class CDSServiceDiscoveryView(
    APIView
):
    authentication_classes = [
        CDSServiceJWTAuthentication,
    ]

    permission_classes = [
        RequiredCDSServiceScopePermission,
    ]

    required_service_scope = (
        "cds.discovery.read"
    )

    @extend_schema(
        operation_id="api_cds_001",
        summary="CDS Service Discovery",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiResponse(
                description=(
                    "CDS_AUTH_REQUIRED"
                ),
            ),
            403: OpenApiResponse(
                description="CDS_FORBIDDEN",
            ),
        },
        tags=["CDS Hooks"],
    )
    def get(
        self,
        request,
    ):
        return Response(
            {
                "services": (
                    CDS_SERVICES
                )
            },
            status=status.HTTP_200_OK,
        )


class MedicationSafetyOrderSelectView(
    APIView
):
    authentication_classes = [
        CDSServiceJWTAuthentication,
    ]

    permission_classes = [
        RequiredCDSServiceScopePermission,
    ]

    required_service_scope = (
        "cds.medication-safety.invoke"
    )

    @extend_schema(
        operation_id="api_cds_002",
        summary=(
            "Medication Safety "
            "order-select"
        ),
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiResponse(
                description=(
                    "CDS_HOOK_INVALID_REQUEST / "
                    "CDS_HOOK_UNSUPPORTED"
                ),
            ),
            401: OpenApiResponse(
                description=(
                    "CDS_AUTH_REQUIRED"
                ),
            ),
            403: OpenApiResponse(
                description="CDS_FORBIDDEN",
            ),
            404: OpenApiResponse(
                description=(
                    "PATIENT_CONTEXT_NOT_FOUND"
                ),
            ),
        },
        tags=["CDS Hooks"],
    )
    def post(
        self,
        request,
    ):
        try:
            result = (
                evaluate_medication_safety_cds_hook(
                    payload=request.data,
                    expected_hook=(
                        "order-select"
                    ),
                )
            )

        except CDSHookError as exc:
            raise ContractAPIException(
                exc.code,
                exc.detail,
                exc.status_code,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class MedicationSafetyOrderSignView(
    APIView
):
    authentication_classes = [
        CDSServiceJWTAuthentication,
    ]

    permission_classes = [
        RequiredCDSServiceScopePermission,
    ]

    required_service_scope = (
        "cds.medication-safety.invoke"
    )

    @extend_schema(
        operation_id="api_cds_003",
        summary=(
            "Medication Safety "
            "order-sign"
        ),
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiResponse(
                description=(
                    "CDS_HOOK_INVALID_REQUEST / "
                    "CDS_HOOK_UNSUPPORTED"
                ),
            ),
            401: OpenApiResponse(
                description=(
                    "CDS_AUTH_REQUIRED"
                ),
            ),
            403: OpenApiResponse(
                description="CDS_FORBIDDEN",
            ),
            404: OpenApiResponse(
                description=(
                    "PATIENT_CONTEXT_NOT_FOUND"
                ),
            ),
        },
        tags=["CDS Hooks"],
    )
    def post(
        self,
        request,
    ):
        try:
            result = (
                evaluate_medication_safety_cds_hook(
                    payload=request.data,
                    expected_hook=(
                        "order-sign"
                    ),
                )
            )

        except CDSHookError as exc:
            raise ContractAPIException(
                exc.code,
                exc.detail,
                exc.status_code,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


from apps.cdss.services.stroke_patient_view import (
    StrokePatientViewError,
    evaluate_stroke_patient_view,
)


class StrokePatientView(APIView):
    authentication_classes = [
        CDSServiceJWTAuthentication,
    ]

    permission_classes = [
        RequiredCDSServiceScopePermission,
    ]

    required_service_scope = (
        "cds.stroke.invoke"
    )

    @extend_schema(
        operation_id="api_cds_004",
        summary=(
            "Stroke Patient View CDS"
        ),
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiResponse(
                description=(
                    "INVALID_HOOK_REQUEST"
                ),
            ),
            401: OpenApiResponse(
                description=(
                    "CDS_AUTH_REQUIRED"
                ),
            ),
            403: OpenApiResponse(
                description="CDS_FORBIDDEN",
            ),
            404: OpenApiResponse(
                description=(
                    "PATIENT_CONTEXT_NOT_FOUND"
                ),
            ),
            503: OpenApiResponse(
                description=(
                    "CDS_DEPENDENCY_UNAVAILABLE"
                ),
            ),
        },
        tags=["CDS Hooks"],
    )
    def post(
        self,
        request,
    ):
        principal = getattr(
            request,
            "user",
            None,
        )

        try:
            result = (
                evaluate_stroke_patient_view(
                    payload=request.data,
                    service_principal=(
                        principal
                    ),
                    request_id=getattr(
                        request,
                        "request_id",
                        None,
                    ),
                )
            )

        except StrokePatientViewError as exc:
            raise ContractAPIException(
                exc.code,
                exc.detail,
                exc.status_code,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
