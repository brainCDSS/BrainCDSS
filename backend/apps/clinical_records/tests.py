import uuid

from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Role, User
from apps.clinical_records.api.encounter_serializers import (
    EncounterCreateSerializer,
)
from apps.clinical_records.api.encounter_views import EncounterCreateView
from apps.audit.models import AuditLog
from apps.clinical_records.api.generated_real_149 import (
    ContractView000,
    ContractView001,
    ContractView002,
)
from apps.clinical_records.models import ClinicalNote, Encounter
from apps.common.models import OutboxEvent
from apps.patients.models import Patient


class EncounterCreateSerializerTests(SimpleTestCase):
    def test_walk_in_outpatient_does_not_require_appointment(self):
        serializer = EncounterCreateSerializer(data={
            "patient_id": str(uuid.uuid4()),
            "encounter_type": "OUTPATIENT",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("appointment_id", serializer.validated_data)

    def test_confirmed_appointment_identifier_can_be_supplied(self):
        appointment_id = uuid.uuid4()
        serializer = EncounterCreateSerializer(data={
            "patient_id": str(uuid.uuid4()),
            "encounter_type": "OUTPATIENT",
            "appointment_id": str(appointment_id),
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["appointment_id"], appointment_id)

    def test_identifiers_must_be_uuid(self):
        serializer = EncounterCreateSerializer(data={
            "patient_id": "not-a-uuid",
            "encounter_type": "OUTPATIENT",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("patient_id", serializer.errors)


class EncounterListViewTests(TestCase):
    def setUp(self):
        self.role = Role.objects.create(code="NEUROLOGIST", name="Neurologist")
        self.user = User.objects.create_user(
            login_id="encounter-list-doctor",
            password="test-password",
            name="Encounter Doctor",
            role=self.role,
        )
        self.patient = Patient.objects.create(
            patient_no="P-ENC-LIST-001",
            name="Encounter Patient",
            created_by=self.user,
        )
        self.other_patient = Patient.objects.create(
            patient_no="P-ENC-LIST-002",
            name="Other Patient",
            created_by=self.user,
        )
        now = timezone.now()
        self.older = self._create_encounter(
            self.patient,
            "ENC-LIST-OLDER",
            "REGISTERED",
            now - timedelta(hours=2),
        )
        self.newer = self._create_encounter(
            self.patient,
            "ENC-LIST-NEWER",
            "IN_PROGRESS",
            now - timedelta(hours=1),
            started_at=now - timedelta(minutes=50),
        )
        self._create_encounter(
            self.other_patient,
            "ENC-LIST-OTHER",
            "IN_PROGRESS",
            now,
        )
        self.factory = APIRequestFactory()

    def _create_encounter(
        self,
        patient,
        encounter_no,
        encounter_status,
        arrived_at,
        started_at=None,
    ):
        return Encounter.objects.create(
            patient=patient,
            encounter_no=encounter_no,
            encounter_type="OUTPATIENT",
            status=encounter_status,
            arrived_at=arrived_at,
            started_at=started_at,
            created_at=arrived_at,
            updated_at=arrived_at,
        )

    def get(self, params):
        request = self.factory.get("/api/v1/encounters", params)
        force_authenticate(request, user=self.user)
        return EncounterCreateView.as_view()(request)

    def test_patient_encounters_are_returned_latest_first(self):
        response = self.get({"patient_id": str(self.patient.id)})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data],
            [str(self.newer.id), str(self.older.id)],
        )
        self.assertEqual(
            set(response.data[0]),
            {
                "id",
                "patient_id",
                "encounter_no",
                "encounter_type",
                "status",
                "arrived_at",
                "started_at",
                "ended_at",
            },
        )

    def test_status_filter_is_applied(self):
        response = self.get({
            "patient_id": str(self.patient.id),
            "status": "REGISTERED",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.older.id))

    def test_patient_id_is_required(self):
        response = self.get({})

        self.assertEqual(response.status_code, 400)
        self.assertIn("patient_id", response.data["error"]["details"])

    def test_status_must_be_supported(self):
        response = self.get({
            "patient_id": str(self.patient.id),
            "status": "COMPLETED",
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data["error"]["details"])


class ClinicalNoteWriteApiTests(TestCase):
    def setUp(self):
        self.neurologist_role = Role.objects.create(
            code="NEUROLOGIST",
            name="Neurologist",
        )
        self.nurse_role = Role.objects.create(code="NURSE", name="Nurse")
        self.author = self._create_user("clinical-note-author", self.neurologist_role)
        self.other_doctor = self._create_user(
            "clinical-note-other-doctor",
            self.neurologist_role,
        )
        self.nurse = self._create_user("clinical-note-nurse", self.nurse_role)
        self.patient = Patient.objects.create(
            patient_no="P-CLINICAL-NOTE-001",
            name="Clinical Note Patient",
            created_by=self.author,
        )
        now = timezone.now()
        self.encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="ENC-CLINICAL-NOTE-001",
            encounter_type="OUTPATIENT",
            status="IN_PROGRESS",
            arrived_at=now,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self.factory = APIRequestFactory()

    @staticmethod
    def _create_user(login_id, role):
        return User.objects.create_user(
            login_id=login_id,
            password="test-password",
            name=login_id,
            role=role,
        )

    def _request(self, view, method, path, user, data=None, **kwargs):
        request = getattr(self.factory, method)(path, data or {}, format="json")
        force_authenticate(request, user=user)
        return view.as_view()(request, **kwargs)

    def _create_note(self, *, author=None, status="DRAFT", **fields):
        now = timezone.now()
        return ClinicalNote.objects.create(
            encounter=self.encounter,
            author=author or self.author,
            status=status,
            created_at=now,
            updated_at=now,
            **fields,
        )

    def test_post_sets_authenticated_author_and_draft_status(self):
        response = self._request(
            ContractView000,
            "post",
            "/api/v1/clinical-notes",
            self.author,
            {
                "encounter_id": str(self.encounter.id),
                "subjective": "headache",
                "author_id": str(self.other_doctor.id),
                "status": "FINAL",
            },
        )

        self.assertEqual(response.status_code, 201)
        note = ClinicalNote.objects.get()
        self.assertEqual(note.author, self.author)
        self.assertEqual(note.status, "DRAFT")
        self.assertEqual(response.data["note_id"], str(note.id))
        self.assertTrue(
            OutboxEvent.objects.filter(
                aggregate=str(note.id),
                event_type="clinical_note_created",
            ).exists()
        )

    def test_post_rejects_non_neurologist_and_missing_encounter(self):
        forbidden = self._request(
            ContractView000,
            "post",
            "/api/v1/clinical-notes",
            self.nurse,
            {"encounter_id": str(self.encounter.id)},
        )
        missing = self._request(
            ContractView000,
            "post",
            "/api/v1/clinical-notes",
            self.author,
            {"encounter_id": str(uuid.uuid4())},
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(ClinicalNote.objects.count(), 0)

    def test_post_prevents_duplicate_draft_for_encounter_and_author(self):
        self._create_note()

        response = self._request(
            ContractView000,
            "post",
            "/api/v1/clinical-notes",
            self.author,
            {"encounter_id": str(self.encounter.id)},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(ClinicalNote.objects.count(), 1)

    def test_patch_only_updates_allowed_fields_on_own_draft(self):
        note = self._create_note(subjective="before")

        response = self._request(
            ContractView001,
            "patch",
            f"/api/v1/clinical-notes/{note.id}",
            self.author,
            {"subjective": "after", "clinical_opinion": "opinion"},
            note_id=note.id,
        )

        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.subjective, "after")
        self.assertEqual(note.clinical_opinion, "opinion")
        self.assertEqual(note.status, "DRAFT")

    def test_patch_rejects_other_author_final_note_and_managed_field(self):
        own_draft = self._create_note()
        other_response = self._request(
            ContractView001,
            "patch",
            f"/api/v1/clinical-notes/{own_draft.id}",
            self.other_doctor,
            {"subjective": "not allowed"},
            note_id=own_draft.id,
        )
        managed_response = self._request(
            ContractView001,
            "patch",
            f"/api/v1/clinical-notes/{own_draft.id}",
            self.author,
            {"status": "FINAL"},
            note_id=own_draft.id,
        )
        final_note = self._create_note(author=self.other_doctor, status="FINAL")
        final_response = self._request(
            ContractView001,
            "patch",
            f"/api/v1/clinical-notes/{final_note.id}",
            self.other_doctor,
            {"subjective": "not allowed"},
            note_id=final_note.id,
        )

        self.assertEqual(other_response.status_code, 403)
        self.assertEqual(managed_response.status_code, 400)
        self.assertEqual(final_response.status_code, 409)

    def test_finalize_requires_complete_clinical_findings(self):
        note = self._create_note(assessment="assessment", plan="plan")

        response = self._request(
            ContractView002,
            "post",
            f"/api/v1/clinical-notes/{note.id}/finalize",
            self.author,
            note_id=note.id,
        )

        self.assertEqual(response.status_code, 400)
        note.refresh_from_db()
        self.assertEqual(note.status, "DRAFT")
        self.assertIsNone(note.finalized_at)

    def test_finalize_rejects_other_author(self):
        note = self._create_note(
            assessment="assessment",
            plan="plan",
            clinical_opinion="clinical opinion",
        )

        response = self._request(
            ContractView002,
            "post",
            f"/api/v1/clinical-notes/{note.id}/finalize",
            self.other_doctor,
            note_id=note.id,
        )

        self.assertEqual(response.status_code, 403)
        note.refresh_from_db()
        self.assertEqual(note.status, "DRAFT")
        self.assertIsNone(note.finalized_at)

    def test_finalize_changes_state_and_records_audit_and_outbox(self):
        note = self._create_note(
            assessment="assessment",
            plan="plan",
            clinical_opinion="clinical opinion",
        )

        response = self._request(
            ContractView002,
            "post",
            f"/api/v1/clinical-notes/{note.id}/finalize",
            self.author,
            note_id=note.id,
        )

        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.status, "FINAL")
        self.assertIsNotNone(note.finalized_at)
        self.assertTrue(
            AuditLog.objects.filter(
                action="API-NOTE-005",
                resource=str(note.id),
            ).exists()
        )
        self.assertTrue(
            OutboxEvent.objects.filter(
                aggregate=str(note.id),
                event_type="clinical_note_finalized",
            ).exists()
        )

        repeated = self._request(
            ContractView002,
            "post",
            f"/api/v1/clinical-notes/{note.id}/finalize",
            self.author,
            note_id=note.id,
        )
        self.assertEqual(repeated.status_code, 409)
