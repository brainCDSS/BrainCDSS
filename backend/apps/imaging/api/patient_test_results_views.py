from django.db.models import F
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.imaging.models import ImagingStudy
from apps.organizations.api.permissions import IsPatientRole
from apps.patients.selectors.patients import patient_profile_for_user


class PatientTestResultsView(APIView):
    """Read-only imaging-study projection scoped to the current patient."""

    permission_classes = [IsAuthenticated, IsPatientRole]

    def get(self, request):
        patient = patient_profile_for_user(request.user)
        if patient is None:
            return Response({"results": []})

        studies = (
            ImagingStudy.objects.filter(patient_id=patient.id)
            .order_by(F("study_datetime").desc(nulls_last=True), "-created_at")
        )
        return Response(
            {
                "results": [
                    {
                        "study_id": study.id,
                        "study_datetime": study.study_datetime,
                        "modalities": study.modalities
                        if isinstance(study.modalities, list)
                        else [],
                        "study_description": study.study_description,
                    }
                    for study in studies
                ]
            }
        )
