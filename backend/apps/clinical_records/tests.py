import uuid

from django.test import SimpleTestCase

from apps.clinical_records.api.encounter_serializers import (
    EncounterCreateSerializer,
)


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
