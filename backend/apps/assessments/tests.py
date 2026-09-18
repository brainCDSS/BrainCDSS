from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, User
from apps.assessments.models import AssessmentItem, EmergencyEvent, InitialAssessment
from apps.audit.models import AuditLog
from apps.clinical_records.models import Encounter
from apps.notifications.models import Notification
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


class EmergencyWorklistAPITests(APITestCase):
    def setUp(self):
        self.neurologist_role = Role.objects.create(
            code=RoleCode.NEUROLOGIST,
            name="Neurologist",
        )
        self.nurse_role = Role.objects.create(
            code=RoleCode.NURSE,
            name="Nurse",
        )
        self.neurologist = User.objects.create_user(
            login_id="emergency-neurologist",
            password="test-password",
            name="Assigned neurologist",
            role=self.neurologist_role,
        )
        self.other_neurologist = User.objects.create_user(
            login_id="other-neurologist",
            password="test-password",
            name="Other neurologist",
            role=self.neurologist_role,
        )
        self.nurse = User.objects.create_user(
            login_id="emergency-nurse",
            password="test-password",
            name="Assessment nurse",
            role=self.nurse_role,
        )
        self.patient = Patient.objects.create(
            patient_no="EMERGENCY-001",
            name="Emergency patient",
            estimated_age=68,
            sex="M",
            created_by=self.nurse,
        )
        now = timezone.now()
        self.encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="ENC-EMERGENCY-001",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.assessment = InitialAssessment.objects.create(
            encounter=self.encounter,
            assessor=self.nurse,
            assigned_neurologist=self.neurologist,
            status="COMPLETED",
            total_score=12,
            triage_priority="EMERGENCY",
            lkw_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
        self.event = EmergencyEvent.objects.create(
            assessment=self.assessment,
            encounter=self.encounter,
            assigned_neurologist=self.neurologist,
            event_type="EMERGENCY_DETECTED",
            priority="EMERGENCY",
            status="NOTIFIED",
            occurred_at=now,
            notified_at=now,
            created_at=now,
        )
        self.worklist_url = reverse("api-asm-006-real")
        self.acknowledge_url = reverse("api-evt-001-real", args=[self.event.id])

    def test_assigned_neurologist_receives_emergency_worklist(self):
        self.client.force_authenticate(self.neurologist)

        response = self.client.get(self.worklist_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(item["assessment_id"], str(self.assessment.id))
        self.assertEqual(item["encounter_id"], str(self.encounter.id))
        self.assertEqual(item["patient_summary"]["patient_no"], "EMERGENCY-001")
        self.assertEqual(item["triage_priority"], "EMERGENCY")
        self.assertEqual(item["event"]["id"], str(self.event.id))

    def test_other_neurologist_does_not_receive_assigned_event(self):
        self.client.force_authenticate(self.other_neurologist)

        response = self.client.get(self.worklist_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_nurse_cannot_access_emergency_worklist(self):
        self.client.force_authenticate(self.nurse)

        response = self.client.get(self.worklist_url)

        self.assertEqual(response.status_code, 403)

    def test_assigned_neurologist_can_acknowledge_event(self):
        self.client.force_authenticate(self.neurologist)

        response = self.client.post(self.acknowledge_url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ACKNOWLEDGED")
        self.assertEqual(response.data["acknowledged_by"], str(self.neurologist.id))
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "ACKNOWLEDGED")
        self.assertEqual(self.event.acknowledged_by_id, self.neurologist.id)
        self.assertIsNotNone(self.event.acknowledged_at)
        self.assertTrue(
            AuditLog.objects.filter(
                action="ACKNOWLEDGE_EMERGENCY_EVENT",
                resource=str(self.event.id),
                outcome="SUCCESS",
            ).exists()
        )

    def test_event_cannot_be_acknowledged_twice(self):
        self.client.force_authenticate(self.neurologist)
        self.client.post(self.acknowledge_url, {}, format="json")

        response = self.client.post(self.acknowledge_url, {}, format="json")

        self.assertEqual(response.status_code, 409)

    def test_other_neurologist_cannot_acknowledge_event(self):
        self.client.force_authenticate(self.other_neurologist)

        response = self.client.post(self.acknowledge_url, {}, format="json")

        self.assertEqual(response.status_code, 403)


class AssessmentEncounterListAPITests(APITestCase):
    def setUp(self):
        self.neurologist_role = Role.objects.create(
            code=RoleCode.NEUROLOGIST,
            name="Neurologist",
        )
        self.nurse_role = Role.objects.create(
            code=RoleCode.NURSE,
            name="Nurse",
        )
        self.neurosurgeon_role = Role.objects.create(
            code=RoleCode.NEUROSURGEON,
            name="Neurosurgeon",
        )
        self.radiology_role = Role.objects.create(
            code=RoleCode.RADIOLOGY,
            name="Radiology",
        )
        self.patient_role = Role.objects.create(
            code=RoleCode.PATIENT,
            name="Patient",
        )
        self.neurologist = User.objects.create_user(
            login_id="assessment-list-neurologist",
            password="test-password",
            name="Assessment neurologist",
            role=self.neurologist_role,
        )
        self.nurse = User.objects.create_user(
            login_id="assessment-list-nurse",
            password="test-password",
            name="Assessment nurse",
            role=self.nurse_role,
        )
        self.neurosurgeon = User.objects.create_user(
            login_id="assessment-list-neurosurgeon",
            password="test-password",
            name="Assessment neurosurgeon",
            role=self.neurosurgeon_role,
        )
        self.radiologist = User.objects.create_user(
            login_id="assessment-list-radiologist",
            password="test-password",
            name="Assessment radiologist",
            role=self.radiology_role,
        )
        self.patient_user = User.objects.create_user(
            login_id="assessment-list-patient",
            password="test-password",
            name="Assessment patient",
            role=self.patient_role,
        )
        self.patient = Patient.objects.create(
            patient_no="ASSESSMENT-LIST-001",
            name="Assessment List Patient",
            created_by=self.nurse,
        )
        self.encounter = Encounter.objects.create(
            patient=self.patient,
            encounter_no="ENC-ASSESSMENT-LIST-001",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=timezone.now(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.url = reverse("api-asm-assessment-list-by-encounter")

    def _create_assessment(self, **kwargs):
        now = timezone.now()
        return InitialAssessment.objects.create(
            encounter=self.encounter,
            assessor=self.nurse,
            status="COMPLETED",
            created_at=now,
            updated_at=now,
            **kwargs,
        )

    def test_neurologist_reads_assessment_by_encounter_with_items(self):
        assessment = self._create_assessment(
            total_score=7,
            triage_priority="EMERGENCY",
            symptom_note="Assessment symptom",
            assigned_neurologist=self.neurologist,
        )
        AssessmentItem.objects.create(
            assessment=assessment,
            item_group="FAST",
            item_code="FAST_FACE",
            value_text="ABNORMAL",
            is_red_flag=True,
            recorded_at=timezone.now(),
        )

        self.client.force_authenticate(self.neurologist)
        response = self.client.get(self.url, {"encounter_id": self.encounter.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(item["assessment_id"], str(assessment.id))
        self.assertEqual(item["encounter_id"], str(self.encounter.id))
        self.assertEqual(item["total_score"], 7)
        self.assertEqual(item["items"][0]["item_code"], "FAST_FACE")

    def test_returns_empty_results_when_encounter_has_no_assessment(self):
        self.client.force_authenticate(self.neurologist)

        response = self.client.get(self.url, {"encounter_id": self.encounter.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"count": 0, "results": []})

    def test_all_authorized_clinical_roles_read_assessments_by_encounter(self):
        for user in (
            self.neurologist,
            self.neurosurgeon,
            self.radiologist,
            self.nurse,
        ):
            with self.subTest(role=user.role.code):
                self.client.force_authenticate(user)
                response = self.client.get(
                    self.url,
                    {"encounter_id": self.encounter.id},
                )

                self.assertEqual(response.status_code, 200)

    def test_rejects_unknown_encounter_and_non_clinical_role(self):
        self.client.force_authenticate(self.neurologist)
        missing = self.client.get(self.url, {"encounter_id": "00000000-0000-0000-0000-000000000000"})

        self.client.force_authenticate(self.patient_user)
        forbidden = self.client.get(self.url, {"encounter_id": self.encounter.id})

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(forbidden.status_code, 403)


class InitialScreeningAssessmentAPITests(APITestCase):
    def setUp(self):
        role = Role.objects.create(code=RoleCode.NURSE, name="Nurse")
        neurologist_role = Role.objects.create(
            code=RoleCode.NEUROLOGIST,
            name="Neurologist",
        )
        self.nurse = User.objects.create_user(
            login_id="screening-nurse",
            password="test-password",
            name="Screening nurse",
            role=role,
        )
        self.client.force_authenticate(self.nurse)
        self.neurologist = User.objects.create_user(
            login_id="screening-neurologist",
            password="test-password",
            name="Screening neurologist",
            role=neurologist_role,
        )
        patient = Patient.objects.create(
            patient_no="SCREENING-001",
            name="Screening patient",
            created_by=self.nurse,
        )
        encounter = Encounter.objects.create(
            patient=patient,
            encounter_no="ENC-SCREENING-001",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=timezone.now(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.assessment = InitialAssessment.objects.create(
            encounter=encounter,
            assessor=self.nurse,
            assigned_neurologist=self.neurologist,
            status="DRAFT",
            triage_priority="URGENT",
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.detail_url = reverse("api-asm-003-real", args=[self.assessment.id])
        self.complete_url = f"/api/v1/assessments/{self.assessment.id}/complete"

    def test_items_upsert_and_completion_calculates_initial_screening_total(self):
        scores = {
            "BALANCE": 1,
            "EYES": 2,
            "FACE": 3,
            "ARM": 4,
            "SPEECH": 5,
            "CONSCIOUSNESS": 2,
        }
        response = self.client.patch(
            self.detail_url,
            {
                "onset_at": None,
                "lkw_at": timezone.now().isoformat(),
                "symptom_note": "screening",
                "items": [
                    *[
                        {"item_code": code, "value_numeric": score}
                        for code, score in scores.items()
                    ],
                    {"item_code": "FAST_FACE", "value_text": "ABNORMAL"},
                    {"item_code": "FAST_ARM", "value_text": "NORMAL"},
                    {"item_code": "FAST_SPEECH", "value_text": "NORMAL"},
                    {"item_code": "BP_SYS", "value_numeric": 148, "unit": "mmHg"},
                    {"item_code": "BP_DIA", "value_numeric": 86, "unit": "mmHg"},
                    {"item_code": "HEART_RATE", "value_numeric": 78, "unit": "bpm"},
                    {"item_code": "BODY_TEMP", "value_numeric": 36.8, "unit": "°C"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssessmentItem.objects.filter(assessment=self.assessment).count(), 13)
        self.assertTrue(AssessmentItem.objects.filter(
            assessment=self.assessment,
            item_code="BALANCE",
            item_group="INITIAL_SCREENING",
            value_numeric=1,
            score=1,
        ).exists())
        self.assertTrue(AssessmentItem.objects.filter(
            assessment=self.assessment,
            item_code="FAST_FACE",
            value_text="ABNORMAL",
        ).exists())

        self.client.patch(
            self.detail_url,
            {"items": [{"item_code": "BALANCE", "value_numeric": 5}]},
            format="json",
        )
        self.assertEqual(AssessmentItem.objects.filter(
            assessment=self.assessment,
            item_code="BALANCE",
        ).count(), 1)

        response = self.client.post(
            self.complete_url,
            {"assigned_neurologist_id": str(self.neurologist.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_score"], 21)
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.total_score, 21)
        self.assertEqual(self.assessment.triage_priority, "URGENT")
        self.assertTrue(Notification.objects.filter(
            recipient_user=self.neurologist,
            category="EMERGENCY",
        ).exists())
        self.assertTrue(EmergencyEvent.objects.filter(
            assessment=self.assessment,
            assigned_neurologist=self.neurologist,
            priority="URGENT",
            status="NOTIFIED",
        ).exists())
