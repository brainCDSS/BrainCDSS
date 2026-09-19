from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.api.permissions import IsPatientRole
from apps.patients.selectors.clinical_history import (
    clinical_history_record,
    clinical_history_records,
)
from apps.patients.selectors.patients import patient_profile_for_user


class PatientClinicalHistoryListView(APIView):
    permission_classes = [IsAuthenticated, IsPatientRole]

    def get(self, request):
        patient = patient_profile_for_user(request.user)
        results = clinical_history_records(patient) if patient else []
        return Response({"count": len(results), "next": None, "previous": None, "results": results})


class PatientClinicalHistoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPatientRole]

    def get(self, request, encounter_id):
        patient = patient_profile_for_user(request.user)
        record = clinical_history_record(patient, encounter_id) if patient else None
        if record is None:
            return Response({"detail": "Clinical history not found."}, status=404)
        return Response(record)
