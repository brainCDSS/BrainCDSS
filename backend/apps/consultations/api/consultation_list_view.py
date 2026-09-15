from rest_framework.response import Response

from apps.common.remaining149_runtime import _role_code, check_access
from apps.consultations.api.generated_real_149 import ContractView000, SPECS
from apps.consultations.models import Consultation
from apps.organizations.models import Clinician


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
