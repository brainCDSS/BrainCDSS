from __future__ import annotations

from django.core.paginator import EmptyPage, Paginator
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.rbac import role_allowed
from apps.assessments.models import (
    AssessmentItem,
    InitialAssessment,
)
from apps.patients.api.errors import DomainAPIException
from apps.patients.api.permissions import (
    has_permission_code,
    role_code,
)
from apps.patients.api.serializers import (
    FavoriteHospitalListResponseSerializer,
    FavoriteHospitalPutResponseSerializer,
    PatientCreateResponseSerializer,
    PatientCreateSerializer,
    PatientDetailResponseSerializer,
    PatientIdentifyResponseSerializer,
    PatientIdentifySerializer,
    PatientListQuerySerializer,
    PatientListResponseSerializer,
    PatientMergeResponseSerializer,
    PatientMergeSerializer,
    PatientUpdateResponseSerializer,
    PatientUpdateSerializer,
    TemporaryPatientCreateSerializer,
    TemporaryPatientResponseSerializer,
)
from apps.patients.selectors.patients import (
    can_view_patient,
    get_active_hospital,
    get_patient,
    list_favorite_hospitals,
    list_patients,
    patient_profile_for_user,
    resolve_patient,
)
from apps.patients.services.patients import (
    PatientServiceError,
    add_favorite_hospital,
    create_patient,
    create_temporary_patient,
    identify_temporary_patient,
    merge_temporary_patient,
    remove_favorite_hospital,
    update_patient,
)


PAGE_SIZE = 20

CLINICAL_READ_ROLES = {
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
}


def _raise_service_error(exc: PatientServiceError):
    raise DomainAPIException(
        code=exc.code,
        detail=exc.detail,
        status_code=exc.status_code,
    )


def _validate(serializer):
    if not serializer.is_valid():
        raise DomainAPIException(
            code="VALIDATION_ERROR",
            detail=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return serializer.validated_data


def _require(
    request,
    *,
    roles: set[str],
    permission_code: str | None = None,
):
    current_role = role_code(request.user)

    if not role_allowed(
        current_role,
        roles,
    ):
        raise DomainAPIException(
            code="FORBIDDEN_ROLE",
            detail="The current role cannot access this API.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if (
        permission_code is not None
        and not has_permission_code(
            request.user,
            permission_code,
        )
    ):
        raise DomainAPIException(
            code="FORBIDDEN_ROLE",
            detail=(
                f"Missing permission: {permission_code}"
            ),
            status_code=status.HTTP_403_FORBIDDEN,
        )


def _page_link(request, page_number):
    if page_number is None:
        return None

    params = request.query_params.copy()
    params["page"] = page_number

    return request.build_absolute_uri(
        f"{request.path}?{params.urlencode()}"
    )



def _latest_patient_assessment_snapshot(patient_id):
    qs = (
        InitialAssessment.objects
        .filter(
            encounter__patient_id=patient_id
        )
        .select_related(
            "assigned_neurologist"
        )
        .order_by(
            "-updated_at",
            "-created_at",
        )
    )

    assessment = (
        qs.filter(
            status="COMPLETED"
        ).first()
        or qs.first()
    )

    if assessment is None:
        return None

    items = (
        AssessmentItem.objects
        .filter(
            assessment=assessment
        )
        .order_by(
            "recorded_at",
            "id",
        )
    )

    return {
        "assessment_id": str(
            assessment.id
        ),
        "encounter_id": str(
            assessment.encounter_id
        ),
        "status": assessment.status,
        "total_score":
            assessment.total_score,
        "triage_priority":
            assessment.triage_priority,
        "onset_at":
            assessment.onset_at,
        "lkw_at":
            assessment.lkw_at,
        "symptom_note":
            assessment.symptom_note,

        "assigned_neurologist": (
            {
                "id": str(
                    assessment
                    .assigned_neurologist_id
                ),
                "name": (
                    assessment
                    .assigned_neurologist
                    .name
                ),
            }
            if assessment
            .assigned_neurologist_id
            else None
        ),

        "items": [
            {
                "item_code":
                    item.item_code,

                "value_text":
                    item.value_text,

                "value_numeric":
                    item.value_numeric,

                "unit":
                    item.unit,

                "score":
                    item.score,

                "is_red_flag":
                    item.is_red_flag,

                "note":
                    item.note,
            }
            for item in items
        ],

        "created_at":
            assessment.created_at,

        "updated_at":
            assessment.updated_at,
    }


def _patient_list_item(patient):
    return {
        "id": patient.id,
        "patient_no": patient.patient_no,
        "name": patient.name,
        "birth_date": patient.birth_date,
        "estimated_age": patient.estimated_age,
        "sex": patient.sex,
        "phone": patient.phone,
        "allergy_info": patient.allergy_info,
        "status": patient.status,
    }


def _patient_create_response(patient):
    return {
        "id": patient.id,
        "patient_no": patient.patient_no,
        "name": patient.name,
        "birth_date": patient.birth_date,
        "estimated_age": patient.estimated_age,
        "sex": patient.sex,
        "phone": patient.phone,
        "emergency_contact": patient.emergency_contact,
        "status": patient.status,
        "created_at": patient.created_at,
    }


class PatientListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_pat_001_patient_list",
        tags=["Patient"],
        parameters=[PatientListQuerySerializer],
        responses={200: PatientListResponseSerializer},
    )
    def get(self, request):
        _require(
            request,
            roles=CLINICAL_READ_ROLES,
            permission_code="patient.read",
        )

        query = PatientListQuerySerializer(
            data=request.query_params
        )
        data = _validate(query)

        qs = list_patients(
            actor=request.user,
            search=data.get("search"),
            patient_no=data.get("patient_no"),
            birth_date=data.get("birth_date"),
            status=data.get("status"),
            scope=data.get("scope", "all"),
            user=request.user,
        )

        paginator = Paginator(qs, PAGE_SIZE)

        try:
            page = paginator.page(data["page"])
        except EmptyPage:
            page = paginator.page(
                paginator.num_pages or 1
            )

        return Response({
            "count": paginator.count,
            "next": _page_link(
                request,
                page.next_page_number()
                if page.has_next()
                else None,
            ),
            "previous": _page_link(
                request,
                page.previous_page_number()
                if page.has_previous()
                else None,
            ),
            "results": [
                _patient_list_item(patient)
                for patient in page.object_list
            ],
        })

    @extend_schema(
        operation_id="api_pat_002_patient_create",
        tags=["Patient"],
        request=PatientCreateSerializer,
        responses={201: PatientCreateResponseSerializer},
    )
    def post(self, request):
        _require(
            request,
            roles={"NURSE"},
            permission_code="patient.create",
        )

        serializer = PatientCreateSerializer(
            data=request.data
        )
        data = _validate(serializer)

        try:
            patient = create_patient(
                actor=request.user,
                request=request,
                **data,
            )
        except PatientServiceError as exc:
            _raise_service_error(exc)

        return Response(
            _patient_create_response(patient),
            status=status.HTTP_201_CREATED,
        )


class TemporaryPatientCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_pat_003_temporary_patient_create",
        tags=["Patient"],
        request=TemporaryPatientCreateSerializer,
        responses={201: TemporaryPatientResponseSerializer},
    )
    def post(self, request):
        _require(
            request,
            roles={"NURSE"},
            permission_code="patient.create",
        )

        serializer = (
            TemporaryPatientCreateSerializer(
                data=request.data
            )
        )
        data = _validate(serializer)

        try:
            patient = create_temporary_patient(
                actor=request.user,
                request=request,
                **data,
            )
        except PatientServiceError as exc:
            _raise_service_error(exc)

        return Response(
            {
                "id": patient.id,
                "patient_no": patient.patient_no,
                "name": patient.name,
                "birth_date": None,
                "estimated_age":
                    patient.estimated_age,
                "sex": patient.sex,
                "status": patient.status,
                "created_by": {
                    "id": patient.created_by_id,
                    "name": request.user.name,
                },
                "created_at": patient.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class PatientDetailUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_pat_004_patient_detail",
        tags=["Patient"],
        responses={200: PatientDetailResponseSerializer},
    )
    def get(self, request, patient_id):
        _require(
            request,
            roles=CLINICAL_READ_ROLES,
            permission_code="patient.read",
        )

        original = get_patient(patient_id)

        if original is None or not can_view_patient(request.user, patient_id):
            raise DomainAPIException(
                code="PATIENT_NOT_FOUND",
                detail="Patient was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        resolved, resolved_from = (
            resolve_patient(original)
        )

        if resolved is None:
            raise DomainAPIException(
                code="PATIENT_NOT_FOUND",
                detail=(
                    "Merged patient target could not be resolved."
                ),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        merged_into = None
        merged_at = resolved.merged_at

        if resolved_from is not None:
            merged_into = {
                "id": resolved.id,
                "patient_no": resolved.patient_no,
            }
            merged_at = original.merged_at

        return Response({
            "id": resolved.id,
            "patient_no": resolved.patient_no,
            "name": resolved.name,
            "birth_date": resolved.birth_date,
            "estimated_age": resolved.estimated_age,
            "sex": resolved.sex,
            "phone": resolved.phone,
            "emergency_contact": resolved.emergency_contact,
            "allergy_info": resolved.allergy_info,
            "pregnancy_status": resolved.pregnancy_status,
            "pregnancy_status_updated_at":
                resolved.pregnancy_status_updated_at,
            "status": resolved.status,

            "latest_assessment": (
                _latest_patient_assessment_snapshot(
                    resolved.id
                )
            ),

            "merged_into": merged_into,
            "resolved_from_patient_id": (
                resolved_from
                if resolved_from is not None
                else None
            ),
            "merged_at": merged_at,
            "created_at": resolved.created_at,
            "updated_at": resolved.updated_at,
        })

    @extend_schema(
        operation_id="api_pat_005_patient_update",
        tags=["Patient"],
        request=PatientUpdateSerializer,
        responses={200: PatientUpdateResponseSerializer},
    )
    def patch(self, request, patient_id):
        _require(
            request,
            roles={"NURSE"},
            permission_code="patient.update",
        )

        serializer = PatientUpdateSerializer(
            data=request.data
        )
        data = _validate(serializer)

        try:
            patient = update_patient(
                patient_id=patient_id,
                actor=request.user,
                request=request,
                changes=data,
            )
        except PatientServiceError as exc:
            _raise_service_error(exc)

        return Response({
            "id": patient.id,
            "patient_no": patient.patient_no,
            "name": patient.name,
            "birth_date": patient.birth_date,
            "sex": patient.sex,
            "phone": patient.phone,
            "emergency_contact": patient.emergency_contact,
            "pregnancy_status": patient.pregnancy_status,
            "pregnancy_status_updated_at":
                patient.pregnancy_status_updated_at,
            "status": patient.status,
            "updated_at": patient.updated_at,
        })


class PatientMergeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_pat_006_patient_merge",
        tags=["Patient"],
        request=PatientMergeSerializer,
        responses={200: PatientMergeResponseSerializer},
    )
    def post(self, request, temp_patient_id):
        _require(
            request,
            roles={"NURSE"},
            permission_code="patient.merge",
        )

        serializer = PatientMergeSerializer(
            data=request.data
        )
        data = _validate(serializer)

        try:
            result = merge_temporary_patient(
                source_patient_id=temp_patient_id,
                target_patient_id=data["target_patient_id"],
                actor=request.user,
                request=request,
            )
        except PatientServiceError as exc:
            _raise_service_error(exc)

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class PatientIdentifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_pat_007_patient_identify",
        tags=["Patient"],
        request=PatientIdentifySerializer,
        responses={200: PatientIdentifyResponseSerializer},
    )
    def post(self, request, patient_id):
        _require(
            request,
            roles={"NURSE"},
            permission_code="patient.identify",
        )

        serializer = PatientIdentifySerializer(
            data=request.data
        )
        data = _validate(serializer)

        try:
            patient = identify_temporary_patient(
                patient_id=patient_id,
                actor=request.user,
                request=request,
                **data,
            )
        except PatientServiceError as exc:
            _raise_service_error(exc)

        return Response({
            "id": patient.id,
            "patient_no": patient.patient_no,
            "name": patient.name,
            "birth_date": patient.birth_date,
            "estimated_age": None,
            "sex": patient.sex,
            "phone": patient.phone,
            "emergency_contact": patient.emergency_contact,
            "status": patient.status,
            "updated_at": patient.updated_at,
        })


class FavoriteHospitalListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_fav_001_favorite_hospital_list",
        tags=["Favorite"],
        responses={200: FavoriteHospitalListResponseSerializer},
    )
    def get(self, request):
        _require(
            request,
            roles={"PATIENT"},
            permission_code="favorite.manage",
        )

        patient = patient_profile_for_user(
            request.user
        )

        if patient is None:
            raise DomainAPIException(
                code="PATIENT_NOT_FOUND",
                detail="Patient profile was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        favorites = list_favorite_hospitals(
            patient
        )

        return Response({
            "results": [
                {
                    "hospital_id": item.hospital_id,
                    "name": item.hospital.name,
                    "address": item.hospital.address,
                    "phone": item.hospital.phone,
                    "latitude": item.hospital.latitude,
                    "longitude": item.hospital.longitude,
                    "created_at": item.created_at,
                }
                for item in favorites
            ]
        })


class FavoriteHospitalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_fav_002_favorite_hospital_put",
        tags=["Favorite"],
        request=None,
        responses={
            200: FavoriteHospitalPutResponseSerializer,
            201: FavoriteHospitalPutResponseSerializer,
        },
    )
    def put(self, request, hospital_id):
        _require(
            request,
            roles={"PATIENT"},
            permission_code="favorite.manage",
        )

        patient = patient_profile_for_user(
            request.user
        )

        if patient is None:
            raise DomainAPIException(
                code="PATIENT_NOT_FOUND",
                detail="Patient profile was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        hospital = get_active_hospital(
            hospital_id
        )

        if hospital is None:
            raise DomainAPIException(
                code="HOSPITAL_NOT_FOUND",
                detail="Active hospital was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        relation, created = add_favorite_hospital(
            patient=patient,
            hospital=hospital,
        )

        return Response(
            {
                "hospital_id": hospital.id,
                "favorite": True,
                "created_at": relation.created_at,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )

    @extend_schema(
        operation_id="api_fav_003_favorite_hospital_delete",
        tags=["Favorite"],
        request=None,
        responses={204: None},
    )
    def delete(self, request, hospital_id):
        _require(
            request,
            roles={"PATIENT"},
            permission_code="favorite.manage",
        )

        patient = patient_profile_for_user(
            request.user
        )

        if patient is None:
            raise DomainAPIException(
                code="PATIENT_NOT_FOUND",
                detail="Patient profile was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        hospital = get_active_hospital(
            hospital_id
        )

        if hospital is None:
            raise DomainAPIException(
                code="HOSPITAL_NOT_FOUND",
                detail="Active hospital was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        removed = remove_favorite_hospital(
            patient=patient,
            hospital=hospital,
        )

        if not removed:
            raise DomainAPIException(
                code="HOSPITAL_NOT_FOUND",
                detail=(
                    "Favorite hospital relation "
                    "was not found."
                ),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
