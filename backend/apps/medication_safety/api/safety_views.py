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
from apps.patients.models import Patient
from apps.medication_safety.api.permissions import (
    MedicationSafetyCheckPermission,
)
from apps.medication_safety.api.safety_serializers import (
    MedicationSafetyRequestSerializer,
)
from apps.medication_safety.services.medication_safety import (
    MedicationSafetyError,
    check_medication_safety,
)


class MedicationSafetyCheckView(APIView):
    permission_classes = [
        MedicationSafetyCheckPermission,
    ]

    @extend_schema(
        operation_id="api_medsafe_001",
        summary="처방 안전성 검사",
        description=(
            "로컬 DUR DB 기반 처방 안전성 검사. "
            "현재 runtime 구현 범위는 "
            "INTERACTION(DDI)과 DOSE이다."
        ),
        request=(
            MedicationSafetyRequestSerializer
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "safe, alerts, context"
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "MEDICATION_SAFETY_INPUT_INVALID"
                ),
            ),
            403: OpenApiResponse(
                description=(
                    "FORBIDDEN_ROLE / "
                    "FORBIDDEN_PERMISSION"
                ),
            ),
            404: OpenApiResponse(
                description="PATIENT_NOT_FOUND",
            ),
        },
        tags=["medication_safety"],
    )
    def post(self, request):
        serializer = (
            MedicationSafetyRequestSerializer(
                data=request.data
            )
        )

        if not serializer.is_valid():
            raise ContractAPIException(
                "MEDICATION_SAFETY_INPUT_INVALID",
                str(serializer.errors),
                400,
            )

        data = serializer.validated_data

        patient = (
            Patient.objects
            .filter(
                pk=data["patient_id"],
                status="ACTIVE",
            )
            .first()
        )

        if patient is None:
            raise ContractAPIException(
                "PATIENT_NOT_FOUND",
                "Active patient was not found.",
                404,
            )

        try:
            result = check_medication_safety(
                medications=(
                    data["medications"]
                ),
                patient=patient,
            )

        except MedicationSafetyError as exc:
            raise ContractAPIException(
                "MEDICATION_SAFETY_INPUT_INVALID",
                (
                    f"{exc.code}: "
                    f"{exc.detail}"
                ),
                400,
            )

        result["context"][
            "pregnancy_status"
        ] = patient.pregnancy_status

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
