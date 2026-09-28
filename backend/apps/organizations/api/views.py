from __future__ import annotations

from django.core.paginator import EmptyPage, Paginator
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.api.errors import DomainAPIException
from apps.organizations.api.permissions import (
    IsPatientNurseOrDoctorRole,
    IsPatientOrNurseRole,
    IsPatientRole,
)
from apps.organizations.api.serializers import (
    ClinicianListQuerySerializer,
    DepartmentClinicianResponseSerializer,
    HospitalDepartmentResponseSerializer,
    HospitalDetailResponseSerializer,
    HospitalListQuerySerializer,
    HospitalListResponseSerializer,
)
from apps.organizations.selectors.organizations import (
    favorite_hospital_ids_for_user,
    get_active_department,
    get_active_hospital,
    haversine_km,
    list_active_clinicians,
    list_active_departments,
    list_active_hospitals,
)


PAGE_SIZE = 20


def _page_link(request, page_number: int | None):
    if page_number is None:
        return None

    params = request.query_params.copy()
    params["page"] = page_number
    return request.build_absolute_uri(
        f"{request.path}?{params.urlencode()}"
    )


class HospitalListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_ref_001_hospital_list",
        tags=["Reference"],
        parameters=[HospitalListQuerySerializer],
        responses={200: HospitalListResponseSerializer},
    )
    def get(self, request):
        query = HospitalListQuerySerializer(
            data=request.query_params
        )
        query.is_valid(raise_exception=True)
        data = query.validated_data

        hospitals = list(
            list_active_hospitals(
                search=data.get("search")
            )
        )

        favorite_ids = favorite_hospital_ids_for_user(
            request.user
        )

        lat = data.get("lat")
        lng = data.get("lng")

        rows = []

        for hospital in hospitals:
            distance_km = None

            if (
                lat is not None
                and lng is not None
                and hospital.latitude is not None
                and hospital.longitude is not None
            ):
                distance_km = round(
                    haversine_km(
                        float(lat),
                        float(lng),
                        float(hospital.latitude),
                        float(hospital.longitude),
                    ),
                    2,
                )

            rows.append({
                "id": hospital.id,
                "name": hospital.name,
                "address": hospital.address,
                "phone": hospital.phone,
                "latitude": hospital.latitude,
                "longitude": hospital.longitude,
                "distance_km": distance_km,
                "is_favorite": (
                    str(hospital.id) in favorite_ids
                ),
            })

        if lat is not None and lng is not None:
            rows.sort(
                key=lambda row: (
                    row["distance_km"] is None,
                    row["distance_km"]
                    if row["distance_km"] is not None
                    else float("inf"),
                    row["name"],
                )
            )

        paginator = Paginator(rows, PAGE_SIZE)

        try:
            page = paginator.page(data["page"])
        except EmptyPage:
            page = paginator.page(paginator.num_pages or 1)

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
            "results": list(page.object_list),
        })


class HospitalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_ref_002_hospital_detail",
        tags=["Reference"],
        responses={200: HospitalDetailResponseSerializer},
    )
    def get(self, request, hospital_id):
        hospital = get_active_hospital(hospital_id)

        if hospital is None:
            raise DomainAPIException(
                code="HOSPITAL_NOT_FOUND",
                detail="Active hospital was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        favorite_ids = favorite_hospital_ids_for_user(
            request.user
        )

        departments = list_active_departments(hospital)

        return Response({
            "id": hospital.id,
            "name": hospital.name,
            "address": hospital.address,
            "phone": hospital.phone,
            "latitude": hospital.latitude,
            "longitude": hospital.longitude,
            "departments": [
                {
                    "id": department.id,
                    "code": department.code,
                    "name": department.name,
                }
                for department in departments
            ],
            "is_favorite": (
                str(hospital.id) in favorite_ids
            ),
        })


class HospitalDepartmentListView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsPatientOrNurseRole,
    ]

    @extend_schema(
        operation_id="api_ref_003_hospital_departments",
        tags=["Reference"],
        responses={200: HospitalDepartmentResponseSerializer},
    )
    def get(self, request, hospital_id):
        hospital = get_active_hospital(hospital_id)

        if hospital is None:
            raise DomainAPIException(
                code="HOSPITAL_NOT_FOUND",
                detail="Active hospital was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        departments = list_active_departments(hospital)

        return Response({
            "hospital": {
                "id": hospital.id,
                "name": hospital.name,
            },
            "departments": [
                {
                    "id": department.id,
                    "code": department.code,
                    "name": department.name,
                }
                for department in departments
            ],
        })


class DepartmentClinicianListView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsPatientNurseOrDoctorRole,
    ]

    @extend_schema(
        operation_id="api_ref_004_department_clinicians",
        tags=["Reference"],
        parameters=[ClinicianListQuerySerializer],
        responses={200: DepartmentClinicianResponseSerializer},
    )
    def get(self, request, department_id):
        query = ClinicianListQuerySerializer(
            data=request.query_params
        )
        query.is_valid(raise_exception=True)

        department = get_active_department(department_id)

        if department is None:
            raise DomainAPIException(
                code="DEPARTMENT_NOT_FOUND",
                detail="Active department was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # API-REF-004 currently binds only to Clinician.
        # date is validated for forward compatibility; once an
        # appointment/availability source is added, filtering belongs
        # here without changing the endpoint contract.
        clinicians = list_active_clinicians(department)

        return Response({
            "department": {
                "id": department.id,
                "name": department.name,
            },
            "clinicians": [
                {
                    "id": clinician.id,
                    "user_id": clinician.user_id,
                    "name": clinician.user.name,
                    "specialty": clinician.specialty,
                    "license_no": clinician.license_no,
                    "is_active": clinician.is_active,
                }
                for clinician in clinicians
            ],
        })
