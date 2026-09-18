from datetime import date

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Role, User
from apps.patients.api.patient_profile_views import PatientProfileView
from apps.patients.models import Patient


class PatientProfileViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        patient_role = Role.objects.create(code="PATIENT", name="Patient")
        self.user = User.objects.create_user(
            login_id="profile-patient",
            password="test-password",
            name="Profile patient",
            role=patient_role,
        )
        self.patient = Patient.objects.create(
            user=self.user,
            patient_no="PROFILE-PATIENT",
            name="Profile patient",
            birth_date="1990-05-12",
            sex="M",
            phone="010-1111-2222",
            emergency_contact="010-3333-4444",
            allergy_info="Penicillin",
            created_by=self.user,
        )
        self.other_user = User.objects.create_user(
            login_id="other-profile-patient",
            password="test-password",
            name="Other patient",
            role=patient_role,
        )
        Patient.objects.create(
            user=self.other_user,
            patient_no="OTHER-PROFILE-PATIENT",
            name="Other patient",
            birth_date="1980-01-01",
            created_by=self.other_user,
        )

    def test_returns_only_the_signed_in_patients_allowed_fields(self):
        request = self.factory.get("/api/v1/me/profile")
        force_authenticate(request, user=self.user)

        response = PatientProfileView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {
                "name": "Profile patient",
                "birth_date": date(1990, 5, 12),
                "sex": "M",
                "phone": "010-1111-2222",
                "emergency_contact": "010-3333-4444",
                "allergy_info": "Penicillin",
            },
        )

    def test_returns_null_fields_when_signed_in_patient_has_no_profile(self):
        request = self.factory.get("/api/v1/me/profile")
        force_authenticate(request, user=self.user)
        Patient.objects.filter(pk=self.patient.pk).delete()

        response = PatientProfileView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {
            "name", "birth_date", "sex", "phone", "emergency_contact", "allergy_info"
        })
        self.assertTrue(all(value is None for value in response.data.values()))
