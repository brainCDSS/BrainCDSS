from apps.common.remaining149_runtime import execute_contract
from apps.medications.api.generated_real_149 import ContractView001


MEDICATION_INTAKE_DELETE_SPEC = {
    "api_id": "API-MED-004",
    "app": "medications",
    "domain": "Medication",
    "api_name": "Delete medication intake",
    "method": "DELETE",
    "endpoint": "/api/v1/medication-intakes/{intake_id}",
    "django_path": "api/v1/medication-intakes/<uuid:intake_id>",
    "roles": ["PATIENT"],
    "permission": None,
    "service_scope": None,
    "request_contract": "Path: intake_id: UUID, required",
    "validation": (
        "Authenticated patient may delete only an intake for their own final "
        "prescription schedule."
    ),
    "related_db": (
        "MedicationIntake (medication_intakes), "
        "MedicationSchedule (medication_schedules)"
    ),
    "processing": (
        "Delete the intake only; the schedule and prescription remain unchanged."
    ),
    "response_contract": "-",
    "success": "204 No Content",
    "error_contract": "404 MEDICATION_INTAKE_NOT_FOUND",
    "transaction": "O(required)",
    "transactional": True,
    "event": "MEDICATION_INTAKE_DELETED",
    "note": "PENDING remains a derived schedule state when no intake exists.",
    "primary_model": "medications.MedicationIntake",
    "audit_required": True,
}


class MedicationIntakeDetailView(ContractView001):
    def delete(self, request, **kwargs):
        return execute_contract(request, MEDICATION_INTAKE_DELETE_SPEC, **kwargs)
