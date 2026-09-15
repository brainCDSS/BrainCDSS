from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinical_records.api.encounter_serializers import (
    EncounterCreateResponseSerializer,
    EncounterCreateSerializer,
    EncounterListQuerySerializer,
    EncounterListResponseSerializer,
)
from apps.clinical_records.models import Encounter
from apps.clinical_records.services.encounters import (
    EncounterRegistrationError,
    register_encounter,
)


class EncounterAPIException(APIException):
    def __init__(self, error):
        self.status_code = error.status_code
        super().__init__({"code": error.code, "detail": error.detail})


class EncounterCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_enc_list",
        summary="Encounter 조회",
        parameters=[EncounterListQuerySerializer],
        responses={200: EncounterListResponseSerializer(many=True)},
        tags=["clinical-records"],
    )
    def get(self, request):
        query = EncounterListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        encounters = Encounter.objects.filter(
            patient_id=query.validated_data["patient_id"],
        )
        requested_status = query.validated_data.get("status")
        if requested_status:
            encounters = encounters.filter(status=requested_status)

        encounters = encounters.order_by("-arrived_at")
        return Response(
            EncounterListResponseSerializer(encounters, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="api_enc_001",
        summary="Encounter 등록",
        description=(
            "NURSE가 진료를 등록합니다. OUTPATIENT에서 appointment_id가 "
            "없으면 당일 방문(Walk-in)으로 등록합니다."
        ),
        request=EncounterCreateSerializer,
        responses={201: EncounterCreateResponseSerializer},
        tags=["clinical-records"],
    )
    def post(self, request):
        role_code = getattr(getattr(request.user, "role", None), "code", None)
        if role_code != "NURSE":
            error = EncounterRegistrationError(
                "FORBIDDEN_ROLE",
                "Only nurses may register encounters.",
                403,
            )
            raise EncounterAPIException(error)

        serializer = EncounterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = register_encounter(
                **serializer.validated_data,
                actor_user=request.user,
                request_ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.headers.get("User-Agent") or None,
            )
        except EncounterRegistrationError as error:
            raise EncounterAPIException(error) from error

        return Response(result, status=status.HTTP_201_CREATED)
