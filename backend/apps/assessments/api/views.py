from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assessments.api.generated_real_149 import ContractView000, ContractView002
from apps.assessments.api.serializers import (
    AssessmentEncounterListResponseSerializer,
    AssessmentEncounterQuerySerializer,
    AssessmentWorklistResponseSerializer,
    EmergencyEventAcknowledgeResponseSerializer,
    EmergencyWorklistResponseSerializer,
    TriageReviewCreateSerializer,
    TriageReviewListResponseSerializer,
)
from apps.assessments.models import (
    AssessmentItem,
    EmergencyEvent,
    InitialAssessment,
    TriageReview,
)
from apps.audit.services.audit_event import record_audit_event
from apps.clinical_records.models import Encounter
from apps.organizations.models import Department


def _require_assessment_read_role(request):
    role_code = getattr(getattr(request.user, "role", None), "code", None)
    if role_code not in {
        "NEUROLOGIST",
        "NEUROSURGEON",
        "RADIOLOGY",
        "NURSE",
    }:
        raise PermissionDenied({
            "code": "FORBIDDEN_ROLE",
            "detail": "Only authorized clinical roles may read assessments.",
        })


def _serialize_assessment_detail(assessment, items):
    assigned_neurologist = assessment.assigned_neurologist
    return {
        "assessment_id": assessment.id,
        "encounter_id": assessment.encounter_id,
        "status": assessment.status,
        "total_score": assessment.total_score,
        "triage_priority": assessment.triage_priority,
        "onset_at": assessment.onset_at,
        "lkw_at": assessment.lkw_at,
        "symptom_note": assessment.symptom_note,
        "assigned_neurologist": (
            {"id": assigned_neurologist.id, "name": assigned_neurologist.name}
            if assigned_neurologist else None
        ),
        "items": [
            {
                "item_code": item.item_code,
                "value_text": item.value_text,
                "value_numeric": item.value_numeric,
                "unit": item.unit,
                "score": item.score,
                "is_red_flag": item.is_red_flag,
                "note": item.note,
            }
            for item in items
        ],
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


class AssessmentListCreateView(ContractView000):
    """Preserve the generated POST endpoint and add encounter-scoped reads."""

    @extend_schema(
        operation_id="api_asm_assessment_list_by_encounter",
        tags=["Assessment"],
        parameters=[AssessmentEncounterQuerySerializer],
        responses={200: AssessmentEncounterListResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        _require_assessment_read_role(request)
        query = AssessmentEncounterQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        encounter_id = query.validated_data["encounter_id"]

        try:
            Encounter.objects.get(pk=encounter_id)
        except Encounter.DoesNotExist as exc:
            raise NotFound({
                "code": "ENCOUNTER_NOT_FOUND",
                "detail": "Encounter was not found.",
            }) from exc

        assessments = list(
            InitialAssessment.objects
            .filter(encounter_id=encounter_id)
            .select_related("assigned_neurologist")
            .order_by("-created_at")
        )
        items_by_assessment = {}
        if assessments:
            for item in AssessmentItem.objects.filter(
                assessment_id__in=[assessment.id for assessment in assessments],
            ).order_by("recorded_at", "id"):
                items_by_assessment.setdefault(item.assessment_id, []).append(item)

        payload = {
            "count": len(assessments),
            "results": [
                _serialize_assessment_detail(
                    assessment,
                    items_by_assessment.get(assessment.id, []),
                )
                for assessment in assessments
            ],
        }
        return Response(AssessmentEncounterListResponseSerializer(payload).data)


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

        status_filter = (request.query_params.get("status") or "").upper()

        queryset = (
            Encounter.objects.select_related("patient")
            .exclude(status="CANCELLED")
            .annotate(
                worklist_assessment_id=Subquery(latest_assessment.values("id")[:1]),
                worklist_assessment_status=Subquery(latest_assessment.values("status")[:1]),
                worklist_triage_priority=Subquery(latest_assessment.values("triage_priority")[:1]),
                worklist_assessment_created_at=Subquery(latest_assessment.values("created_at")[:1]),
            )
        )

        if status_filter == "COMPLETED":
            # Historical/completed view. Completed encounters remain visible
            # here even after the encounter itself has been closed.
            queryset = queryset.filter(worklist_assessment_status="COMPLETED")
        else:
            # Default endpoint behavior remains an active nursing worklist.
            queryset = queryset.exclude(status="COMPLETED").filter(
                Q(worklist_assessment_id__isnull=True)
                | Q(worklist_assessment_status="DRAFT")
            )
            if status_filter == "WAITING":
                queryset = queryset.filter(worklist_assessment_id__isnull=True)
            elif status_filter:
                queryset = queryset.filter(worklist_assessment_status=status_filter)

        queryset = queryset.order_by("-arrived_at", "-created_at")

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


class EmergencyEventAlreadyAcknowledged(APIException):
    status_code = 409
    default_code = "EMERGENCY_EVENT_ALREADY_ACKNOWLEDGED"
    default_detail = "The emergency event has already been acknowledged."


def _require_neurologist(request):
    role_code = getattr(getattr(request.user, "role", None), "code", None)
    if role_code != "NEUROLOGIST":
        raise PermissionDenied({
            "code": "FORBIDDEN_ROLE",
            "detail": "Only neurologists may access the emergency worklist.",
        })


class EmergencyWorklistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_neurologist(request)

        queryset = (
            EmergencyEvent.objects.select_related(
                "assessment",
                "encounter__patient",
            )
            .filter(
                assigned_neurologist=request.user,
                assessment__assigned_neurologist=request.user,
                assessment__status="COMPLETED",
                assessment__triage_priority__in=("URGENT", "EMERGENCY"),
            )
            .order_by("-notified_at", "-occurred_at", "-created_at")
        )

        priority = request.query_params.get("priority", "").strip().upper()
        if priority:
            if priority not in {"URGENT", "EMERGENCY"}:
                raise ValidationError({
                    "priority": "priority must be URGENT or EMERGENCY.",
                })
            queryset = queryset.filter(assessment__triage_priority=priority)

        date_filter = parse_date(request.query_params.get("date", ""))
        if date_filter:
            queryset = queryset.filter(occurred_at__date=date_filter)

        ack_status = request.query_params.get("ack_status", "").strip().upper()
        if ack_status:
            if ack_status == "ACKNOWLEDGED":
                queryset = queryset.filter(acknowledged_at__isnull=False)
            elif ack_status in {"NOTIFIED", "UNACKNOWLEDGED"}:
                queryset = queryset.filter(acknowledged_at__isnull=True)
            else:
                raise ValidationError({
                    "ack_status": (
                        "ack_status must be NOTIFIED, UNACKNOWLEDGED, "
                        "or ACKNOWLEDGED."
                    ),
                })

        paginator = AssessmentWorklistPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        payload = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": [self._serialize_row(event) for event in page],
        }
        return Response(EmergencyWorklistResponseSerializer(payload).data)

    @staticmethod
    def _serialize_row(event):
        assessment = event.assessment
        patient = event.encounter.patient
        return {
            "assessment_id": assessment.id,
            "encounter_id": event.encounter_id,
            "patient_summary": {
                "patient_id": patient.id,
                "patient_no": patient.patient_no,
                "name": patient.name,
                "sex": patient.sex,
                "estimated_age": patient.estimated_age,
            },
            "total_score": assessment.total_score,
            "triage_priority": assessment.triage_priority,
            "lkw_at": assessment.lkw_at,
            "event": {
                "id": event.id,
                "status": event.status,
                "notified_at": event.notified_at,
                "acknowledged_at": event.acknowledged_at,
            },
        }


class EmergencyEventAcknowledgeView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, event_id):
        _require_neurologist(request)

        try:
            event = (
                EmergencyEvent.objects.select_for_update()
                .select_related("encounter")
                .get(pk=event_id)
            )
        except EmergencyEvent.DoesNotExist as exc:
            raise NotFound({
                "code": "EMERGENCY_EVENT_NOT_FOUND",
                "detail": "Emergency event not found.",
            }) from exc

        if event.assigned_neurologist_id != request.user.id:
            raise PermissionDenied({
                "code": "EMERGENCY_EVENT_FORBIDDEN",
                "detail": "This emergency event is assigned to another user.",
            })

        if event.status != "NOTIFIED" or event.acknowledged_at is not None:
            raise EmergencyEventAlreadyAcknowledged()

        acknowledged_at = timezone.now()
        before = {
            "status": event.status,
            "acknowledged_by_id": (
                str(event.acknowledged_by_id)
                if event.acknowledged_by_id
                else None
            ),
            "acknowledged_at": (
                event.acknowledged_at.isoformat()
                if event.acknowledged_at
                else None
            ),
        }
        event.status = "ACKNOWLEDGED"
        event.acknowledged_by = request.user
        event.acknowledged_at = acknowledged_at
        event.save(update_fields=("status", "acknowledged_by", "acknowledged_at"))

        record_audit_event(
            source_service="assessments",
            action="ACKNOWLEDGE_EMERGENCY_EVENT",
            resource_type="EmergencyEvent",
            resource_id=event.id,
            patient_id=event.encounter.patient_id,
            outcome="SUCCESS",
            request=request,
            before_json=before,
            after_json={
                "status": event.status,
                "acknowledged_by_id": str(event.acknowledged_by_id),
                "acknowledged_at": event.acknowledged_at.isoformat(),
            },
        )

        payload = {
            "event_id": event.id,
            "status": event.status,
            "acknowledged_by": request.user.id,
            "acknowledged_at": acknowledged_at,
        }
        return Response(EmergencyEventAcknowledgeResponseSerializer(payload).data)


def _serialize_triage_review(review):
    return {
        "review_id": review.id,
        "assessment_id": review.assessment_id,
        "priority": review.priority,
        "reason": review.reason,
        "reviewer": {
            "id": review.reviewer_id,
            "name": review.reviewer.name,
        },
        "reviewer_role": review.reviewer_role,
        "created_at": review.created_at,
    }


class TriageReviewView(APIView):
    """Append-only neurologist reassessment; nurse initial priority is preserved."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _assessment_for_user(request, assessment_id):
        if getattr(getattr(request.user, "role", None), "code", None) != "NEUROLOGIST":
            raise PermissionDenied({
                "code": "FORBIDDEN_ROLE",
                "detail": "Only neurologists may review triage priority.",
            })

        try:
            return (
                InitialAssessment.objects
                .select_related("encounter__patient", "assigned_neurologist")
                .get(pk=assessment_id)
            )
        except InitialAssessment.DoesNotExist as exc:
            raise NotFound({
                "code": "ASSESSMENT_NOT_FOUND",
                "detail": "Assessment was not found.",
            }) from exc

    def get(self, request, assessment_id):
        assessment = self._assessment_for_user(request, assessment_id)

        if assessment.assigned_neurologist_id != request.user.id:
            raise PermissionDenied({
                "code": "ASSESSMENT_NOT_ASSIGNED",
                "detail": "Only the assigned neurologist may view physician triage reviews.",
            })

        reviews = list(
            TriageReview.objects
            .filter(assessment=assessment)
            .select_related("reviewer")
            .order_by("created_at", "id")
        )
        latest_review = reviews[-1] if reviews else None

        payload = {
            "initial_priority": assessment.triage_priority,
            "effective_priority": (
                latest_review.priority
                if latest_review is not None
                else assessment.triage_priority
            ),
            "latest_review": (
                _serialize_triage_review(latest_review)
                if latest_review is not None
                else None
            ),
            "reviews": [
                _serialize_triage_review(review)
                for review in reviews
            ],
        }
        return Response(
            TriageReviewListResponseSerializer(payload).data,
            status=200,
        )

    @transaction.atomic
    def post(self, request, assessment_id):
        assessment = self._assessment_for_user(request, assessment_id)

        if assessment.status != "COMPLETED":
            raise ValidationError({
                "code": "ASSESSMENT_NOT_COMPLETED",
                "detail": "Only completed assessments can be re-triaged.",
            })
        if assessment.assigned_neurologist_id != request.user.id:
            raise PermissionDenied({
                "code": "ASSESSMENT_NOT_ASSIGNED",
                "detail": "Only the assigned neurologist may re-triage this assessment.",
            })

        serializer = TriageReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        latest_review = (
            TriageReview.objects
            .filter(assessment=assessment)
            .order_by("-created_at", "-id")
            .first()
        )
        previous_effective_priority = (
            latest_review.priority
            if latest_review is not None
            else assessment.triage_priority
        )

        review = TriageReview.objects.create(
            assessment=assessment,
            reviewer=request.user,
            reviewer_role="NEUROLOGIST",
            priority=serializer.validated_data["priority"],
            reason=serializer.validated_data["reason"],
        )

        record_audit_event(
            source_service="assessments",
            action="REVIEW_TRIAGE_PRIORITY",
            resource_type="TriageReview",
            resource_id=review.id,
            patient_id=assessment.encounter.patient_id,
            outcome="SUCCESS",
            request=request,
            reason=review.reason,
            before_json={
                "initial_priority": assessment.triage_priority,
                "effective_priority": previous_effective_priority,
            },
            after_json={
                "initial_priority": assessment.triage_priority,
                "effective_priority": review.priority,
                "review_id": str(review.id),
            },
        )

        reviews = list(
            TriageReview.objects
            .filter(assessment=assessment)
            .select_related("reviewer")
            .order_by("created_at", "id")
        )
        payload = {
            "initial_priority": assessment.triage_priority,
            "effective_priority": review.priority,
            "latest_review": _serialize_triage_review(review),
            "reviews": [
                _serialize_triage_review(item)
                for item in reviews
            ],
        }
        return Response(
            TriageReviewListResponseSerializer(payload).data,
            status=201,
        )
