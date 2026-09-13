from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, User
from apps.assessments.models import InitialAssessment
from apps.clinical_records.models import Encounter
from apps.organizations.models import Department, Hospital
from apps.patients.models import Patient


class AssessmentWorklistAPITests(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(code=RoleCode.NURSE, name="간호사")
        self.nurse = User.objects.create_user(
            login_id="worklist-nurse",
            password="test-password",
            name="테스트 간호사",
            role=self.role,
        )
        self.client.force_authenticate(self.nurse)
        self.patient = Patient.objects.create(
            patient_no="TEST-TRIAGE-001",
            name="김트리아지",
            estimated_age=65,
            sex="M",
            created_by=self.nurse,
        )
        self.encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="ENC-TRIAGE-001",
            encounter_type="EMERGENCY",
            status="REGISTERED",
            arrived_at=timezone.now(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.url = reverse("api-asm-001-real")

    def test_waiting_encounter_contains_patient_summary(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        item = response.data["results"][0]
        self.assertIsNone(item["assessment_id"])
        self.assertEqual(item["encounter_id"], str(self.encounter.id))
        self.assertEqual(item["encounter_type"], "EMERGENCY")
        self.assertEqual(item["status"], "WAITING")
        self.assertEqual(item["patient_summary"]["patient_no"], "TEST-TRIAGE-001")
        self.assertEqual(item["patient_summary"]["name"], "김트리아지")
        self.assertEqual(item["patient_summary"]["estimated_age"], 65)
        self.assertEqual(item["patient_summary"]["sex"], "M")

    def test_draft_encounter_uses_existing_assessment(self):
        assessment = InitialAssessment.objects.create(
            encounter=self.encounter,
            assessor=self.nurse,
            status="DRAFT",
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        item = response.data["results"][0]
        self.assertEqual(item["assessment_id"], str(assessment.id))
        self.assertEqual(item["status"], "DRAFT")

    def test_detail_includes_active_neurology_department_id(self):
        hospital = Hospital.objects.create(
            name="테스트 병원",
            address="테스트 주소",
        )
        department = Department.objects.create(
            hospital=hospital,
            code="NEUROLOGY",
            name="신경과",
        )
        assessment = InitialAssessment.objects.create(
            encounter=self.encounter,
            assessor=self.nurse,
            status="DRAFT",
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        response = self.client.get(
            reverse("api-asm-003-real", args=[assessment.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["neurology_department_id"],
            department.id,
        )

    def test_detail_route_keeps_generated_patch_behavior(self):
        assessment = InitialAssessment.objects.create(
            encounter=self.encounter,
            assessor=self.nurse,
            status="DRAFT",
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        response = self.client.patch(
            reverse("api-asm-003-real", args=[assessment.id]),
            {},
            format="json",
        )

        self.assertNotEqual(response.status_code, 405)
