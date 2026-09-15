from rest_framework.response import Response

from apps.common.remaining149_runtime import _role_code, check_access
from apps.consultations.api.generated_real_149 import ContractView000, SPECS
from apps.consultations.models import Consultation
from apps.organizations.models import Clinician

from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response

from apps.clinical_records.models import Encounter
from apps.consultations.models import Consultation, ConsultationHistory
from apps.common.remaining149_runtime import ContractError, check_access

LIST_SPEC = next(spec for spec in SPECS if spec["api_id"] == "API-CON-002")


def _user_summary(user, clinicians_by_user_id):
    if user is None:
        return None

    clinician = clinicians_by_user_id.get(user.id)
    return {
        "id": str(user.id),
        "name": user.name,
        "department": clinician.department.name if clinician else None,
    }


def _allowed_actions(consultation, user):
    role = _role_code(user)
    if consultation.requested_by_id == user.id:
        if consultation.status in {"REQUESTED", "ACCEPTED", "IN_PROGRESS"}:
            return ["CANCEL"]
        if consultation.status == "RESPONDED":
            return ["VIEW_RESPONSE"]
        return []

    is_target_role = (
        (role == "NEUROSURGEON" and consultation.consultation_type == "NEUROSURGERY")
        or (role == "RADIOLOGY" and consultation.consultation_type == "RADIOLOGY")
    )
    if not is_target_role:
        return []
    if consultation.status == "REQUESTED" and consultation.assigned_to_id is None:
        return ["ACCEPT", "REJECT"]
    if consultation.assigned_to_id != user.id:
        return []
    if consultation.status == "ACCEPTED":
        return ["START", "CANCEL"]
    if consultation.status == "IN_PROGRESS":
        return ["RESPOND", "CANCEL"]
    return []


class ConsultationListCreateView(ContractView000):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from rest_framework.exceptions import NotFound

        from apps.common.remaining149_runtime import _audit, _outbox

        create_spec = next(
            spec for spec in SPECS if spec["api_id"] == "API-CON-001"
        )
        check_access(request, create_spec)

        if not isinstance(request.data, dict):
            raise ContractError({"code": "VALIDATION_ERROR", "detail": "JSON object is required."})

        encounter_id = request.data.get("encounter_id")
        consultation_type = request.data.get("consultation_type")
        assigned_to_id = request.data.get("assigned_to_id")
        priority = request.data.get("priority")
        reason = str(request.data.get("reason") or "").strip()

        errors = {}
        if not encounter_id:
            errors["encounter_id"] = "This field is required."
        if consultation_type not in {"RADIOLOGY", "NEUROSURGERY"}:
            errors["consultation_type"] = "Use RADIOLOGY or NEUROSURGERY."
        if not assigned_to_id:
            errors["assigned_to_id"] = "This field is required."
        if priority not in {"ROUTINE", "URGENT", "STAT"}:
            errors["priority"] = "Use ROUTINE, URGENT, or STAT."
        if not reason:
            errors["reason"] = "This field is required."
        if errors:
            raise ContractError({"code": "VALIDATION_ERROR", **errors})

        try:
            encounter = Encounter.objects.select_for_update().get(pk=encounter_id)
        except (Encounter.DoesNotExist, ValueError) as exc:
            raise NotFound({"code": "ENCOUNTER_NOT_FOUND"}) from exc

        if encounter.status not in {"REGISTERED", "IN_PROGRESS"}:
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "encounter_id": "Consultations require a REGISTERED or IN_PROGRESS encounter.",
            })

        if not Clinician.objects.filter(
            user=request.user,
            department__code="NEUROLOGY",
            is_active=True,
        ).exists():
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "detail": "The requester must be an active neurology clinician.",
            })

        try:
            assignee = Clinician.objects.select_related(
                "user__role",
                "department",
            ).get(user_id=assigned_to_id)
        except (Clinician.DoesNotExist, ValueError) as exc:
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "assigned_to_id": "Select an active clinician user.",
            }) from exc

        expected_role = {
            "NEUROSURGERY": "NEUROSURGEON",
            "RADIOLOGY": "RADIOLOGY",
        }[consultation_type]
        if (
            not assignee.is_active
            or assignee.department.code != consultation_type
            or _role_code(assignee.user) != expected_role
        ):
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "assigned_to_id": "The clinician does not match the consultation type.",
            })

        if Consultation.objects.filter(
            encounter=encounter,
            consultation_type=consultation_type,
            assigned_to_id=assignee.user_id,
            status__in={"REQUESTED", "ACCEPTED", "IN_PROGRESS", "RESPONDED"},
        ).exists():
            from apps.common.remaining149_runtime import ContractConflict

            raise ContractConflict({"code": "CONSULTATION_ACTIVE_DUPLICATE"})

        now = timezone.now()
        consultation = Consultation.objects.create(
            encounter=encounter,
            consultation_type=consultation_type,
            requested_by=request.user,
            assigned_to=assignee.user,
            priority=priority,
            reason=reason,
            status="REQUESTED",
            requested_at=now,
            created_at=now,
            updated_at=now,
        )
        ConsultationHistory.objects.create(
            consultation=consultation,
            from_status=None,
            to_status="REQUESTED",
            changed_by=request.user,
            reason=reason,
            changed_at=now,
        )

        payload = {
            "consultation_id": str(consultation.id),
            "encounter_id": str(consultation.encounter_id),
            "type": consultation.consultation_type,
            "assigned_to_id": str(consultation.assigned_to_id),
            "assigned_to": _user_summary(
                consultation.assigned_to,
                {assignee.user_id: assignee},
            ),
            "priority": consultation.priority,
            "reason": consultation.reason,
            "status": consultation.status,
            "requested_at": consultation.requested_at,
            "allowed_actions": _allowed_actions(consultation, request.user),
        }
        _audit(request, create_spec, consultation, None, payload)
        _outbox(create_spec, consultation, payload)
        return Response(payload, status=201)

    def get(self, request, *args, **kwargs):
        check_access(request, LIST_SPEC)
        queryset = Consultation.objects.select_related(
            "encounter__patient",
            "requested_by",
            "assigned_to",
        )

        for query_name in ("encounter_id", "status", "consultation_type"):
            value = request.query_params.get(query_name)
            if value:
                queryset = queryset.filter(**{query_name: value})
        if request.query_params.get("active_only", "").lower() == "true":
            queryset = queryset.filter(status__in={"REQUESTED", "ACCEPTED", "IN_PROGRESS", "RESPONDED"})

        viewer_relation = request.query_params.get("viewer_relation")
        if viewer_relation == "REQUESTED_BY":
            queryset = queryset.filter(requested_by_id=request.user.id)
        elif viewer_relation == "ASSIGNED_TO":
            queryset = queryset.filter(assigned_to_id=request.user.id)

        queryset = queryset.order_by("-requested_at", "-created_at")
        try:
            page = max(int(request.query_params.get("page", 1) or 1), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(max(int(request.query_params.get("page_size", 50) or 50), 1), 100)
        except (TypeError, ValueError):
            page_size = 50

        total = queryset.count()
        start = (page - 1) * page_size
        rows = list(queryset[start:start + page_size])
        user_ids = {
            user_id
            for consultation in rows
            for user_id in (consultation.requested_by_id, consultation.assigned_to_id)
            if user_id is not None
        }
        clinicians_by_user_id = {
            clinician.user_id: clinician
            for clinician in Clinician.objects.filter(user_id__in=user_ids).select_related("department")
        }

        results = []
        for consultation in rows:
            patient = consultation.encounter.patient
            results.append({
                "consultation_id": str(consultation.id),
                "encounter_id": str(consultation.encounter_id),
                "type": consultation.consultation_type,
                "patient_summary": {
                    "id": str(patient.id),
                    "patient_no": patient.patient_no,
                    "name": patient.name,
                    "birth_date": patient.birth_date,
                    "estimated_age": patient.estimated_age,
                    "sex": patient.sex,
                },
                "priority": consultation.priority,
                "status": consultation.status,
                "requested_by": _user_summary(consultation.requested_by, clinicians_by_user_id),
                "assigned_to": _user_summary(consultation.assigned_to, clinicians_by_user_id),
                "requested_at": consultation.requested_at,
                "accepted_at": consultation.accepted_at,
                "started_at": consultation.started_at,
                "completed_at": consultation.completed_at,
                "response_viewed_at": consultation.response_viewed_at,
                "viewer_relation": "REQUESTED_BY" if consultation.requested_by_id == request.user.id else "ASSIGNED_TO",
                "ui_status": consultation.status,
                "allowed_actions": _allowed_actions(consultation, request.user),
            })

        return Response({
            "count": total,
            "next": page + 1 if start + page_size < total else None,
            "previous": page - 1 if page > 1 else None,
            "results": results,
        }, status=200)
