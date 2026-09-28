from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Role, User
from apps.accounts.api.views import PatientSignupView
from apps.assessments.models import InitialAssessment
from apps.clinical_records.models import ClinicalNote, Encounter
from apps.imaging.models import ImagingOrder
from apps.organizations.models import Clinician, Department, Hospital
from apps.patients.api.clinical_history_views import (
    PatientClinicalHistoryDetailView,
    PatientClinicalHistoryListView,
)
from apps.patients.api.patient_profile_views import PatientProfileView
from apps.patients.models import Patient, PatientCareAssignment
from apps.prescriptions.models import Prescription
from apps.patients.selectors.patients import can_view_patient, list_patients


class PatientProfileViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        patient_role = Role.objects.get(code="PATIENT")
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
        role = Role.objects.get(code="NEUROLOGIST")
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


class PatientClinicalHistoryViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        role = Role.objects.get(code="PATIENT")
        self.user = User.objects.create_user("history-owner", "password", name="History owner", role=role)
        self.other_user = User.objects.create_user("history-other", "password", name="History other", role=role)
        self.patient = Patient.objects.create(patient_no="HISTORY-OWNER", name="Owner", user=self.user, created_by=self.user)
        self.other_patient = Patient.objects.create(patient_no="HISTORY-OTHER", name="Other", user=self.other_user, created_by=self.other_user)
        now = timezone.now()
        self.encounter = Encounter.objects.create(patient=self.patient, encounter_no="HISTORY-1", encounter_type="OUTPATIENT", status="COMPLETED", arrived_at=now, started_at=now, created_at=now, updated_at=now)
        self.other_encounter = Encounter.objects.create(patient=self.other_patient, encounter_no="HISTORY-2", encounter_type="OUTPATIENT", status="COMPLETED", arrived_at=now, created_at=now, updated_at=now)
        ClinicalNote.objects.create(encounter=self.encounter, author=self.user, status="DRAFT", clinical_opinion="draft", created_at=now, updated_at=now)
        ClinicalNote.objects.create(encounter=self.encounter, author=self.user, status="FINAL", clinical_opinion="final opinion", finalized_at=now, created_at=now, updated_at=now)
        ImagingOrder.objects.create(patient=self.patient, encounter=self.encounter, procedure_code="MRI", procedure_name="Brain MRI", modality="MR", priority="ROUTINE", status="ORDERED", reason="test", requested_by=self.user, requested_at=now, created_at=now, updated_at=now)
        Prescription.objects.create(encounter=self.encounter, prescribed_by=self.user, status="FINAL", finalized_at=now, created_at=now, updated_at=now)

    def test_list_is_scoped_to_owner_and_exposes_final_record_data(self):
        request = self.factory.get("/api/v1/me/clinical-history")
        force_authenticate(request, user=self.user)
        response = PatientClinicalHistoryListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["exam_names"], ["Brain MRI"])
        self.assertTrue(response.data["results"][0]["has_prescription"])
        self.assertEqual(response.data["results"][0]["clinical_opinion"], "final opinion")
        self.assertIsNone(response.data["results"][0]["diagnosis_name"])

    def test_detail_exposes_final_opinion_and_blocks_other_patient(self):
        request = self.factory.get(f"/api/v1/me/clinical-history/{self.encounter.id}")
        force_authenticate(request, user=self.user)
        response = PatientClinicalHistoryDetailView.as_view()(request, encounter_id=self.encounter.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["encounter_type"], "OUTPATIENT")
        self.assertEqual(response.data["clinical_opinion"], "final opinion")
        self.assertEqual(response.data["exams"][0]["name"], "Brain MRI")

        request = self.factory.get(f"/api/v1/me/clinical-history/{self.other_encounter.id}")
        force_authenticate(request, user=self.user)
        response = PatientClinicalHistoryDetailView.as_view()(request, encounter_id=self.other_encounter.id)
        self.assertEqual(response.status_code, 404)

    def test_list_returns_no_opinion_when_an_encounter_has_no_final_note(self):
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="HISTORY-NO-FINAL-NOTE",
            encounter_type="OUTPATIENT",
            status="COMPLETED",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )

        request = self.factory.get("/api/v1/me/clinical-history")
        force_authenticate(request, user=self.user)
        response = PatientClinicalHistoryListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        record = next(
            item
            for item in response.data["results"]
            if item["encounter_id"] == str(encounter.id)
        )
        self.assertIsNone(record["clinical_opinion"])

    def test_er_encounter_uses_its_unambiguous_assigned_neurologist(self):
        neurologist_role = Role.objects.get(code="NEUROLOGIST")
        neurologist = User.objects.create_user(
            "history-emergency-neurologist",
            "password",
            name="Emergency neurologist",
            role=neurologist_role,
        )
        hospital = Hospital.objects.create(
            name="History hospital",
            address="Test address",
        )
        department = Department.objects.create(
            hospital=hospital,
            code="HISTORY-NEUROLOGY",
            name="Neurology",
        )
        Clinician.objects.create(
            user=neurologist,
            department=department,
            is_active=True,
        )
        for encounter_type in ("ER", "EMERGENCY"):
            with self.subTest(encounter_type=encounter_type):
                encounter = Encounter.objects.create(
                    patient=self.patient,
                    encounter_no=f"HISTORY-{encounter_type}",
                    encounter_type=encounter_type,
                    status="COMPLETED",
                    arrived_at=timezone.now(),
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                InitialAssessment.objects.create(
                    encounter=encounter,
                    assessor=self.user,
                    assigned_neurologist=neurologist,
                    status="COMPLETED",
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )

                request = self.factory.get(
                    f"/api/v1/me/clinical-history/{encounter.id}"
                )
                force_authenticate(request, user=self.user)
                response = PatientClinicalHistoryDetailView.as_view()(
                    request,
                    encounter_id=encounter.id,
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["department_name"], "Neurology")
                self.assertEqual(
                    response.data["clinician_name"], "Emergency neurologist"
                )

    def test_emergency_encounter_with_multiple_assignees_keeps_care_null(self):
        neurologist_role = Role.objects.get(code="NEUROLOGIST")
        first_neurologist = User.objects.create_user(
            "history-first-neurologist",
            "password",
            name="First neurologist",
            role=neurologist_role,
        )
        second_neurologist = User.objects.create_user(
            "history-second-neurologist",
            "password",
            name="Second neurologist",
            role=neurologist_role,
        )
        encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="HISTORY-AMBIGUOUS-EMERGENCY",
            encounter_type="EMERGENCY",
            status="COMPLETED",
            arrived_at=timezone.now(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        for neurologist in (first_neurologist, second_neurologist):
            InitialAssessment.objects.create(
                encounter=encounter,
                assessor=self.user,
                assigned_neurologist=neurologist,
                status="COMPLETED",
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

        request = self.factory.get(
            f"/api/v1/me/clinical-history/{encounter.id}"
        )
        force_authenticate(request, user=self.user)
        response = PatientClinicalHistoryDetailView.as_view()(
            request,
            encounter_id=encounter.id,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["department_name"])
        self.assertIsNone(response.data["clinician_name"])


class PatientSignupViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.role = Role.objects.get(code="PATIENT")
        self.payload = {"name": "Signup patient", "resident_registration_number": "900512-1234567", "email": "signup@example.com", "phone": "010-1234-5678", "login_id": "signup-patient", "password": "SafePassword123!"}

    @patch("apps.accounts.api.views.generate_patient_no", return_value="P-SIGNUP-1")
    def test_signup_creates_patient_user_with_derived_birth_date_and_sex(self, _):
        response = PatientSignupView.as_view()(self.factory.post("/api/v1/auth/patient-signup", self.payload, format="json"))
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(login_id="signup-patient")
        patient = Patient.objects.get(user=user)
        self.assertEqual(user.role, self.role)
        self.assertTrue(user.check_password("SafePassword123!"))
        self.assertEqual(str(patient.birth_date), "1990-05-12")
        self.assertEqual(patient.sex, "M")

    @patch("apps.accounts.api.views.generate_patient_no", return_value="P-SIGNUP-1")
    def test_signup_rejects_duplicate_identity_and_invalid_registration_number(self, _):
        PatientSignupView.as_view()(self.factory.post("/api/v1/auth/patient-signup", self.payload, format="json"))
        duplicate = PatientSignupView.as_view()(self.factory.post("/api/v1/auth/patient-signup", self.payload, format="json"))
        self.assertEqual(duplicate.status_code, 400)
        invalid = PatientSignupView.as_view()(self.factory.post("/api/v1/auth/patient-signup", {**self.payload, "login_id": "different", "email": "different@example.com", "resident_registration_number": "invalid"}, format="json"))
        self.assertEqual(invalid.status_code, 400)
class NursePatientAccessSelectorTests(TestCase):
    def setUp(self):
        self.role = Role.objects.get(code="NURSE")
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
