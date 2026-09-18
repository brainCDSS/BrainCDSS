from datetime import date

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Role, User
from apps.patients.api.patient_profile_views import PatientProfileView
from apps.patients.models import Patient, PatientCareAssignment
from apps.patients.selectors.patients import can_view_patient, list_patients


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
class PatientCareAssignmentSelectorTests(TestCase):
    def setUp(self):
        role = Role.objects.create(code="NEUROLOGIST", name="Neurologist")
        self.clinician = User.objects.create_user("neuro-test", "password", name="Neurologist", role=role)
        self.other_clinician = User.objects.create_user("neuro-other", "password", name="Other", role=role)
        self.assigned = Patient.objects.create(patient_no="P-ASSIGNED", name="Assigned", created_by=self.clinician)
        self.other = Patient.objects.create(patient_no="P-OTHER", name="Other", created_by=self.clinician)

    def test_active_assignment_scopes_patient_list_and_detail_access(self):
        PatientCareAssignment.objects.create(
            patient=self.assigned,
            clinician=self.clinician,
            role=PatientCareAssignment.AssignmentRole.PRIMARY,
            source=PatientCareAssignment.Source.AI_ANALYSIS,
        )

        self.assertEqual(list(list_patients(actor=self.clinician)), [self.assigned])
        self.assertTrue(can_view_patient(self.clinician, self.assigned.id))
        self.assertFalse(can_view_patient(self.clinician, self.other.id))

    def test_clinician_without_assignments_cannot_access_patients(self):
        self.assertEqual(list(list_patients(actor=self.other_clinician)), [])
        self.assertFalse(can_view_patient(self.other_clinician, self.assigned.id))


class NursePatientAccessSelectorTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(code="NURSE", name="Nurse")
        self.nurse = User.objects.create_user(
            "nurse-access",
            "password",
            name="Nurse",
            role=self.role,
        )
        self.active = Patient.objects.create(
            patient_no="P-NURSE-ACTIVE",
            name="Active patient",
            created_by=self.nurse,
        )
        self.temp = Patient.objects.create(
            patient_no="TMP-NURSE",
            name="Temporary patient",
            status="TEMP",
            created_by=self.nurse,
        )
        self.merged = Patient.objects.create(
            patient_no="P-NURSE-MERGED",
            name="Merged patient",
            status="MERGED",
            created_by=self.nurse,
        )

    def test_nurse_can_access_non_merged_patients_without_assignment(self):
        patients = list(list_patients(actor=self.nurse))

        self.assertIn(self.active, patients)
        self.assertIn(self.temp, patients)
        self.assertNotIn(self.merged, patients)
        self.assertTrue(can_view_patient(self.nurse, self.active.id))
        self.assertTrue(can_view_patient(self.nurse, self.temp.id))
        self.assertFalse(can_view_patient(self.nurse, self.merged.id))
