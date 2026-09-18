from collections import defaultdict

from django.db.models import F
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.api.permissions import IsPatientRole
from apps.patients.selectors.patients import patient_profile_for_user
from apps.prescriptions.models import Prescription, PrescriptionItem


def _item_payload(item):
    return {
        "item_id": item.id,
        "prescription_id": item.prescription_id,
        "medication_id": item.medication_id,
        "medication_code": item.medication_code,
        "medication_name": item.medication_name,
        "dose": str(item.dose),
        "dose_unit": item.dose_unit,
        "route": item.route,
        "frequency_per_day": item.frequency_per_day,
        "timing": item.timing,
        "start_date": item.start_date,
        "duration_days": item.duration_days,
        "instructions": item.instructions,
    }


class PatientPrescriptionsView(APIView):
    """Read-only FINAL prescriptions and items scoped to the current patient."""

    permission_classes = [IsAuthenticated, IsPatientRole]

    def get(self, request):
        patient = patient_profile_for_user(request.user)
        if patient is None:
            return Response({"results": []})

        prescriptions = list(
            Prescription.objects.filter(
                encounter__patient_id=patient.id,
                status="FINAL",
            ).order_by(F("finalized_at").desc(nulls_last=True), "-created_at")
        )
        items_by_prescription = defaultdict(list)
        for item in PrescriptionItem.objects.filter(
            prescription_id__in=[prescription.id for prescription in prescriptions]
        ).order_by("created_at"):
            items_by_prescription[item.prescription_id].append(_item_payload(item))

        return Response(
            {
                "results": [
                    {
                        "prescription_id": prescription.id,
                        "status": prescription.status,
                        "finalized_at": prescription.finalized_at,
                        "items": items_by_prescription[prescription.id],
                    }
                    for prescription in prescriptions
                ]
            }
        )
