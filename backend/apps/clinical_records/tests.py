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
from apps.clinical_records.models import Encounter
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
