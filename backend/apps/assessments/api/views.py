from django.db.models import OuterRef, Q, Subquery
from django.utils.dateparse import parse_date
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.api.generated_real_149 import ContractView002
from apps.assessments.api.serializers import AssessmentWorklistResponseSerializer
from apps.assessments.models import InitialAssessment
from apps.clinical_records.models import Encounter
from apps.organizations.models import Department


class AssessmentDetailView(ContractView002):
    """Keep the generated detail/update behavior and extend only the GET payload."""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        department = (
            Department.objects.filter(
                Q(code__iexact="NEUROLOGY") | Q(name="신경과"),
                is_active=True,
                hospital__is_active=True,
            )
            .order_by("id")
            .first()
        )
        response.data["neurology_department_id"] = (
            department.id if department else None
        )
        return response


class AssessmentWorklistPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class AssessmentWorklistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role_code = getattr(getattr(request.user, "role", None), "code", None)
        if role_code != "NURSE":
            raise PermissionDenied({
                "code": "FORBIDDEN_ROLE",
                "detail": "Only nurses may access the assessment worklist.",
            })

        latest_assessment = InitialAssessment.objects.filter(
            encounter_id=OuterRef("pk"),
        ).order_by("-created_at")

        queryset = (
            Encounter.objects.select_related("patient")
            .exclude(status__in=("COMPLETED", "CANCELLED"))
            .annotate(
                worklist_assessment_id=Subquery(latest_assessment.values("id")[:1]),
                worklist_assessment_status=Subquery(latest_assessment.values("status")[:1]),
                worklist_triage_priority=Subquery(latest_assessment.values("triage_priority")[:1]),
                worklist_assessment_created_at=Subquery(latest_assessment.values("created_at")[:1]),
            )
            .filter(
                Q(worklist_assessment_id__isnull=True)
                | Q(worklist_assessment_status="DRAFT")
            )
            .order_by("-arrived_at", "-created_at")
        )

        status_filter = request.query_params.get("status")
        if status_filter == "WAITING":
            queryset = queryset.filter(worklist_assessment_id__isnull=True)
        elif status_filter:
            queryset = queryset.filter(worklist_assessment_status=status_filter)

        date_filter = parse_date(request.query_params.get("date", ""))
        if date_filter:
            queryset = queryset.filter(arrived_at__date=date_filter)

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(patient__name__icontains=search)
                | Q(patient__patient_no__icontains=search)
                | Q(encounter_no__icontains=search)
            )

        paginator = AssessmentWorklistPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        rows = [self._serialize_row(encounter) for encounter in page]
        payload = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": rows,
        }
        serializer = AssessmentWorklistResponseSerializer(payload)
        return Response(serializer.data)

    @staticmethod
    def _serialize_row(encounter):
        assessment_id = encounter.worklist_assessment_id
        return {
            "assessment_id": assessment_id,
            "encounter_id": encounter.id,
            "encounter_type": encounter.encounter_type,
            "patient_summary": {
                "patient_id": encounter.patient_id,
                "patient_no": encounter.patient.patient_no,
                "name": encounter.patient.name,
                "sex": encounter.patient.sex,
                "estimated_age": encounter.patient.estimated_age,
            },
            "status": encounter.worklist_assessment_status if assessment_id else "WAITING",
            "triage_priority": encounter.worklist_triage_priority,
            "created_at": encounter.worklist_assessment_created_at or encounter.arrived_at,
        }
