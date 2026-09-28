from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role, RoleCode, RolePermission, User
from apps.medication_safety.models import PatientAllergy
from apps.patients.models import Patient


class PatientAllergyAPITests(APITestCase):
    def setUp(self):
        role = Role.objects.get(code=RoleCode.NURSE)
        self.nurse = User.objects.create_user(
            login_id="allergy-nurse",
            password="test-password",
            name="Allergy nurse",
            role=role,
        )
        for code in ("patient_allergy.read", "patient_allergy.manage"):
            permission, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": code, "domain": "patients"},
            )
            RolePermission.objects.get_or_create(role=role, permission=permission)

        self.patient = Patient.objects.create(
            patient_no="ALLERGY-TEST-001",
            name="Allergy test patient",
            created_by=self.nurse,
        )
        self.other_patient = Patient.objects.create(
            patient_no="ALLERGY-TEST-002",
            name="Other patient",
            created_by=self.nurse,
        )
        self.client.force_authenticate(self.nurse)
        self.url = f"/api/v1/patients/{self.patient.id}/allergies"

    def test_create_refreshes_patient_summary_and_lists_only_the_patient(self):
        PatientAllergy.objects.create(
            patient=self.other_patient,
            substance="Other allergy",
            severity="MILD",
            status="ACTIVE",
        )

        response = self.client.post(
            self.url,
            {
                "substance": "Penicillin",
                "reaction": "rash",
                "severity": "SEVERE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["patient_id"], str(self.patient.id))
        self.patient.refresh_from_db()
        self.assertIn("Penicillin", self.patient.allergy_info)
        self.assertIn("severity=SEVERE", self.patient.allergy_info)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["substance"], "Penicillin")
