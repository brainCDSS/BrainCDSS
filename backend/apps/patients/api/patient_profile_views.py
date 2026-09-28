from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.api.permissions import IsPatientRole
from apps.patients.selectors.patients import patient_profile_for_user


class PatientProfileView(APIView):
    """Read-only Patient profile projection scoped to the signed-in patient."""

    permission_classes = [IsAuthenticated, IsPatientRole]

    def get(self, request):
        patient = patient_profile_for_user(request.user)
        if patient is None:
            return Response(
                {
                    "name": None,
                    "birth_date": None,
                    "sex": None,
                    "phone": None,
                    "emergency_contact": None,
                    "allergy_info": None,
                }
            )

        return Response(
            {
                "name": patient.name,
                "birth_date": patient.birth_date,
                "sex": patient.sex,
                "phone": patient.phone,
                "emergency_contact": patient.emergency_contact,
                "allergy_info": patient.allergy_info,
            }
        )
