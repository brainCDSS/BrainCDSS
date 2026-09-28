from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.common.remaining149_runtime import _medm_list
from apps.accounts.models import Role, User
from apps.clinical_records.models import Encounter
from apps.medications.models import Medication, MedicationDiseaseGroup, MedicationIntake, MedicationSchedule
from apps.medications.tasks.reminders import _scheduled_minute_window, send_medication_reminders
from apps.notifications.models import Notification
from apps.patients.models import Patient
from apps.prescriptions.models import Prescription, PrescriptionItem


class MedicationReminderWindowTests(SimpleTestCase):
    def test_uses_only_the_scheduled_minute(self):
        start, end = _scheduled_minute_window(
            datetime(2026, 9, 28, 9, 30, 42, 123456)
        )

        self.assertEqual(start, datetime(2026, 9, 28, 9, 30))
        self.assertEqual(end, datetime(2026, 9, 28, 9, 31))


class MedicationReminderGroupingTests(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=0, microsecond=0)
        role = Role.objects.get(code="PATIENT")
        self.user = User.objects.create_user(
            login_id="reminder-patient",
            password="test-password",
            name="Reminder patient",
            role=role,
        )
        self.patient = Patient.objects.create(
            user=self.user,
            patient_no="REMINDER-PATIENT",
            name="Reminder patient",
            created_by=self.user,
        )
        self.medication = Medication.objects.create(
            medication_code="REMINDER-MEDICATION",
            medication_name="Reminder medication",
            is_active=True,
            created_at=self.now,
            updated_at=self.now,
        )

    def _schedule(self, *, patient=None, at=None, suffix="1"):
        patient = patient or self.patient
        at = at or self.now
        encounter = Encounter.objects.create(
            patient=patient,
            encounter_no=f"REMINDER-ENCOUNTER-{suffix}",
            encounter_type="OUTPATIENT",
            status="COMPLETED",
            arrived_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        prescription = Prescription.objects.create(
            encounter=encounter,
            prescribed_by=patient.user,
            status="FINAL",
            finalized_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        item = PrescriptionItem.objects.create(
            prescription=prescription,
            medication=self.medication,
            medication_code=self.medication.medication_code,
            medication_name=self.medication.medication_name,
            dose="100.00",
            dose_unit="mg",
            frequency_per_day=1,
            timing="MORNING",
            start_date=self.now.date(),
            duration_days=7,
            created_at=self.now,
            updated_at=self.now,
        )
        return MedicationSchedule.objects.create(
            prescription_item=item,
            scheduled_at=at,
            time_slot="MORNING",
            dose="1.00",
            created_at=self.now,
        )

    @patch("apps.medications.tasks.reminders.timezone.now")
    def test_groups_pending_schedules_for_one_patient_and_minute(self, now):
        now.return_value = self.now
        first = self._schedule(suffix="1")
        second = self._schedule(suffix="2")

        result = send_medication_reminders.run()

        self.assertEqual(result["created"], 1)
        notification = Notification.objects.get(category="MEDICATION")
        self.assertEqual(
            {row["medication_schedule_id"] for row in notification.data_json["medication_schedules"]},
            {str(first.id), str(second.id)},
        )
        self.assertEqual(send_medication_reminders.run()["created"], 0)

    @patch("apps.medications.tasks.reminders.timezone.now")
    def test_excludes_taken_schedule_from_group(self, now):
        now.return_value = self.now
        taken = self._schedule(suffix="taken")
        pending = self._schedule(suffix="pending")
        MedicationIntake.objects.create(
            schedule=taken,
            recorded_by=self.user,
            status="TAKEN",
            taken_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )

        send_medication_reminders.run()

        notification = Notification.objects.get(category="MEDICATION")
        self.assertEqual(
            [row["medication_schedule_id"] for row in notification.data_json["medication_schedules"]],
            [str(pending.id)],
        )

    @patch("apps.medications.tasks.reminders.timezone.now")
    def test_separates_patients_and_scheduled_minutes(self, now):
        now.return_value = self.now
        self._schedule(suffix="current")
        self._schedule(at=self.now + timedelta(minutes=1), suffix="next")
        role = Role.objects.get(code="PATIENT")
        other_user = User.objects.create_user(
            login_id="other-reminder-patient",
            password="test-password",
            name="Other reminder patient",
            role=role,
        )
        other_patient = Patient.objects.create(
            user=other_user,
            patient_no="OTHER-REMINDER-PATIENT",
            name="Other reminder patient",
            created_by=other_user,
        )
        self._schedule(patient=other_patient, suffix="other-current")

        self.assertEqual(send_medication_reminders.run()["created"], 2)
        self.assertEqual(Notification.objects.filter(category="MEDICATION").count(), 2)

        now.return_value = self.now + timedelta(minutes=1)
        self.assertEqual(send_medication_reminders.run()["created"], 1)
        self.assertEqual(Notification.objects.filter(category="MEDICATION").count(), 3)

    def test_patient_can_delete_own_taken_intake_and_schedule_returns_pending(self):
        schedule = self._schedule(suffix="delete-own")
        intake = MedicationIntake.objects.create(
            schedule=schedule,
            recorded_by=self.user,
            status="TAKEN",
            taken_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.delete(f"/api/v1/medication-intakes/{intake.id}")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(MedicationIntake.objects.filter(pk=intake.id).exists())
        self.assertTrue(MedicationSchedule.objects.filter(pk=schedule.id).exists())

        schedules_response = client.get(
            "/api/v1/medication-schedules",
            {"date": timezone.localdate(schedule.scheduled_at).isoformat()},
        )
        self.assertEqual(schedules_response.status_code, 200)
        item = next(
            row
            for row in schedules_response.data["items"]
            if row["schedule_id"] == str(schedule.id)
        )
        self.assertEqual(item["status"], "PENDING")
        self.assertIsNone(item["intake_id"])

    def test_patient_cannot_delete_another_patients_intake(self):
        role = Role.objects.get(code="PATIENT")
        other_user = User.objects.create_user(
            login_id="delete-other-patient",
            password="test-password",
            name="Delete other patient",
            role=role,
        )
        other_patient = Patient.objects.create(
            user=other_user,
            patient_no="DELETE-OTHER-PATIENT",
            name="Delete other patient",
            created_by=other_user,
        )
        schedule = self._schedule(patient=other_patient, suffix="delete-other")
        intake = MedicationIntake.objects.create(
            schedule=schedule,
            recorded_by=other_user,
            status="TAKEN",
            taken_at=self.now,
            created_at=self.now,
            updated_at=self.now,
        )
        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.delete(f"/api/v1/medication-intakes/{intake.id}")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(MedicationIntake.objects.filter(pk=intake.id).exists())

    def test_delete_returns_not_found_for_missing_intake(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.delete(
            "/api/v1/medication-intakes/00000000-0000-0000-0000-000000000000"
        )

        self.assertEqual(response.status_code, 404)

    def test_existing_create_and_update_keep_taken_and_skipped_support(self):
        schedule = self._schedule(suffix="existing-intake-actions")
        client = APIClient()
        client.force_authenticate(user=self.user)

        create_response = client.post(
            "/api/v1/medication-intakes",
            {"medication_schedule_id": str(schedule.id), "status": "TAKEN"},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        intake_id = create_response.data["intake_id"]
        update_response = client.patch(
            f"/api/v1/medication-intakes/{intake_id}",
            {"status": "SKIPPED"},
            format="json",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["status"], "SKIPPED")


class MedicationDiseaseGroupSearchTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.factory = APIRequestFactory()
        self.hemorrhage_medication = Medication.objects.create(
            medication_code="SYN-H-001",
            medication_name="Synthetic hemorrhage medication",
            dosage_form="TABLET",
            strength="1 mg",
            manufacturer="Synthetic",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.other_medication = Medication.objects.create(
            medication_code="SYN-I-001",
            medication_name="Synthetic ischemic medication",
            dosage_form="TABLET",
            strength="1 mg",
            manufacturer="Synthetic",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        MedicationDiseaseGroup.objects.create(
            medication=self.hemorrhage_medication,
            disease_group=MedicationDiseaseGroup.DiseaseGroup.HEMORRHAGIC_STROKE,
            evidence_source="synthetic-test-only",
        )

    def test_filters_only_curated_active_disease_group_mappings(self):
        request = Request(self.factory.get(
            "/api/v1/medications",
            {"disease_group": "HEMORRHAGIC_STROKE", "is_active": "True"},
        ))
        response = _medm_list(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(self.hemorrhage_medication.id),
        )

    def test_rejects_unknown_disease_group(self):
        request = Request(self.factory.get(
            "/api/v1/medications",
            {"disease_group": "UNKNOWN"},
        ))
        response = _medm_list(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_QUERY")
