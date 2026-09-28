from django.test import TestCase
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.common.remaining149_runtime import _medm_list
from apps.medications.models import Medication, MedicationDiseaseGroup


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
