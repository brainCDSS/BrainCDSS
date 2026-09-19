from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Role, User
from apps.clinical_records.models import Encounter
from apps.medications.models import Medication
from apps.patients.models import Patient
from apps.prescriptions.api.patient_prescription_views import PatientPrescriptionsView
from apps.prescriptions.models import Prescription, PrescriptionItem


class PatientPrescriptionsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        role = Role.objects.get(code="PATIENT")
        self.user = User.objects.create_user(login_id="patient-prescription", password="test-password", name="Patient", role=role)
        self.patient = Patient.objects.create(user=self.user, patient_no="RX-PATIENT", name="Patient", created_by=self.user)
        self.other_user = User.objects.create_user(login_id="other-patient-prescription", password="test-password", name="Other", role=role)
        self.other_patient = Patient.objects.create(user=self.other_user, patient_no="RX-OTHER", name="Other", created_by=self.other_user)
        self.medication = Medication.objects.create(medication_code="TEST-RX", medication_name="Test medication", is_active=True, created_at=timezone.now(), updated_at=timezone.now())

    def prescription(self, patient, suffix, status, finalized_at):
        now = timezone.now()
        encounter = Encounter.objects.create(patient=patient, encounter_no=f"ENC-{suffix}", encounter_type="OUTPATIENT", status="COMPLETED", arrived_at=now, created_at=now, updated_at=now)
        prescription = Prescription.objects.create(encounter=encounter, prescribed_by=patient.user, status=status, finalized_at=finalized_at, created_at=now, updated_at=now)
        PrescriptionItem.objects.create(prescription=prescription, medication=self.medication, medication_code="TEST-RX", medication_name="Test medication", dose="100.00", dose_unit="mg", frequency_per_day=1, timing="MORNING", start_date=now.date(), duration_days=30, instructions="Take with water.", created_at=now, updated_at=now)
        return prescription

    def test_scopes_to_current_patient_final_prescriptions_newest_first(self):
        now = timezone.now()
        older = self.prescription(self.patient, "1", "FINAL", now - timedelta(days=1))
        newer = self.prescription(self.patient, "2", "FINAL", now)
        self.prescription(self.patient, "3", "DRAFT", None)
        self.prescription(self.other_patient, "4", "FINAL", now + timedelta(days=1))

        request = self.factory.get("/api/v1/me/prescriptions")
        force_authenticate(request, user=self.user)
        response = PatientPrescriptionsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["prescription_id"] for row in response.data["results"]], [newer.id, older.id])
        item = response.data["results"][0]["items"][0]
        self.assertEqual(set(item), {"item_id", "prescription_id", "medication_id", "medication_code", "medication_name", "dose", "dose_unit", "route", "frequency_per_day", "timing", "start_date", "duration_days", "instructions"})
        self.assertEqual(item["medication_name"], "Test medication")

    def test_returns_empty_results_without_final_prescriptions(self):
        request = self.factory.get("/api/v1/me/prescriptions")
        force_authenticate(request, user=self.user)
        response = PatientPrescriptionsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"results": []})
