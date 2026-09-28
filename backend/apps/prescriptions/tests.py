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
from apps.prescriptions.services.prescription_finalize import (
    _create_finalized_prescription_notification,
)
from apps.notifications.models import Notification


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


class FinalizedPrescriptionNotificationTests(TestCase):
    def setUp(self):
        patient_role = Role.objects.get(code="PATIENT")
        clinician_role = Role.objects.get(code="NEUROLOGIST")
        self.patient_user = User.objects.create_user(
            login_id="finalized-prescription-patient",
            password="test-password",
            name="Patient",
            role=patient_role,
        )
        self.clinician = User.objects.create_user(
            login_id="finalized-prescription-clinician",
            password="test-password",
            name="Clinician",
            role=clinician_role,
        )
        now = timezone.now()
        self.patient = Patient.objects.create(
            user=self.patient_user,
            patient_no="FINALIZED-RX-PATIENT",
            name="Patient",
            created_by=self.clinician,
        )
        encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="FINALIZED-RX-ENCOUNTER",
            encounter_type="OUTPATIENT",
            status="COMPLETED",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.prescription = Prescription.objects.create(
            encounter=encounter,
            prescribed_by=self.clinician,
            status="FINAL",
            finalized_at=now,
            created_at=now,
            updated_at=now,
        )

    def test_creates_one_patient_notification_with_finalized_payload(self):
        notification = _create_finalized_prescription_notification(
            prescription=self.prescription,
            patient=self.patient,
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient_user, self.patient_user)
        self.assertEqual(notification.category, "PRESCRIPTION")
        self.assertEqual(notification.severity, "INFO")
        self.assertEqual(notification.data_json["event_type"], "PRESCRIPTION_FINALIZED")
        self.assertEqual(notification.data_json["prescription_id"], str(self.prescription.id))
        self.assertEqual(notification.data_json["patient_id"], str(self.patient.id))
        self.assertEqual(Notification.objects.filter(category="PRESCRIPTION").count(), 1)
        self.assertIsNone(
            _create_finalized_prescription_notification(
                prescription=self.prescription,
                patient=self.patient,
            )
        )

    def test_skips_notification_when_patient_has_no_user(self):
        self.patient.user = None
        self.patient.save(update_fields=["user"])

        notification = _create_finalized_prescription_notification(
            prescription=self.prescription,
            patient=self.patient,
        )

        self.assertIsNone(notification)
        self.assertFalse(Notification.objects.filter(category="PRESCRIPTION").exists())
