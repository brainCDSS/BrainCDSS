from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.api.permissions import role_code
from apps.prescriptions.models import PrescriptionItem


CLINICAL_READ_ROLES = {
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
}


class CurrentMedicationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_current_medications",
        summary="환자 현재 복용 중인 약물 조회",
        responses={status.HTTP_200_OK: {"type": "object"}},
    )
    def get(self, request, patient_id):
        if role_code(request.user) not in CLINICAL_READ_ROLES:
            return Response(
                {"code": "FORBIDDEN_ROLE"},
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()
        items = PrescriptionItem.objects.select_related(
            "prescription__encounter",
            "medication",
        ).filter(
            prescription__encounter__patient_id=patient_id,
            prescription__status="FINAL",
            start_date__lte=today,
        ).order_by("-prescription__finalized_at", "-created_at")

        results = []
        for item in items:
            if item.duration_days <= 0 or today >= item.start_date + timedelta(days=item.duration_days):
                continue
            results.append({
                "item_id": str(item.id),
                "prescription_id": str(item.prescription_id),
                "medication_id": str(item.medication_id),
                "medication_code": item.medication_code,
                "medication_name": item.medication_name,
                "dose": str(item.dose),
                "dose_unit": item.dose_unit,
                "frequency_per_day": item.frequency_per_day,
                "timing": item.timing,
                "start_date": item.start_date,
                "duration_days": item.duration_days,
            })

        return Response({"count": len(results), "results": results})
