from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.common.remaining149_runtime import check_access, serialize_instance
from apps.consultations.api.generated_real_149 import ContractView001, SPECS
from apps.consultations.api.consultation_list_view import _allowed_actions, _user_summary
from apps.consultations.models import Consultation
from apps.organizations.models import Clinician


DETAIL_SPEC = next(spec for spec in SPECS if spec["api_id"] == "API-CON-003")
UI_STATUS = {
    "REQUESTED": "요청됨",
    "ACCEPTED": "수락됨",
    "IN_PROGRESS": "검토 중",
    "RESPONDED": "회신 완료",
    "CLOSED": "종결",
    "REJECTED": "거절",
    "CANCELLED": "취소",
    "EXPIRED": "만료",
}


class ConsultationDetailView(ContractView001):
    def get(self, request, *args, **kwargs):
        check_access(request, DETAIL_SPEC)
        try:
            consultation = Consultation.objects.select_related(
                "encounter__patient",
                "requested_by",
                "assigned_to",
            ).get(
                pk=kwargs["consultation_id"],
            )
        except Consultation.DoesNotExist as exc:
            raise NotFound({"code": "CONSULTATION_NOT_FOUND"}) from exc

        if (
            consultation.requested_by_id != request.user.id
            and consultation.assigned_to_id != request.user.id
        ):
            raise NotFound({"code": "CONSULTATION_NOT_FOUND"})

        user_ids = {
            user_id
            for user_id in (consultation.requested_by_id, consultation.assigned_to_id)
            if user_id is not None
        }
        clinicians_by_user_id = {
            clinician.user_id: clinician
            for clinician in Clinician.objects.filter(user_id__in=user_ids).select_related("department")
        }
        payload = serialize_instance(consultation)
        patient = consultation.encounter.patient
        payload.update({
            "consultation_id": str(consultation.id),
            "type": consultation.consultation_type,
            "patient_summary": {
                "id": str(patient.id),
                "patient_no": patient.patient_no,
                "name": patient.name,
                "birth_date": patient.birth_date,
                "estimated_age": patient.estimated_age,
                "sex": patient.sex,
            },
            "requested_by": _user_summary(consultation.requested_by, clinicians_by_user_id),
            "assigned_to": _user_summary(consultation.assigned_to, clinicians_by_user_id),
            "viewer_relation": "REQUESTED_BY" if consultation.requested_by_id == request.user.id else "ASSIGNED_TO",
            "ui_status": UI_STATUS.get(consultation.status, consultation.status),
            "allowed_actions": _allowed_actions(consultation, request.user),
        })
        return Response(payload, status=200)
