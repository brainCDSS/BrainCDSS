from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.clinical_records.models import Encounter
from apps.consultations.models import Consultation
from apps.organizations.models import Clinician, Department, Hospital
from apps.patients.models import Patient


class ConsultationListResponseTests(APITestCase):
    def setUp(self):
        neurologist_role = Role.objects.create(code="NEUROLOGIST", name="Neurologist")
        surgeon_role = Role.objects.create(code="NEUROSURGEON", name="Neurosurgeon")
        self.requester = User.objects.create_user("requester", "password", name="요청의", role=neurologist_role)
        self.assignee = User.objects.create_user("assignee", "password", name="담당의", role=surgeon_role)
        hospital = Hospital.objects.create(name="테스트 병원", address="서울")
        neurology = Department.objects.create(hospital=hospital, code="NEUROLOGY", name="신경과")
        surgery = Department.objects.create(hospital=hospital, code="NEUROSURGERY", name="신경외과")
        Clinician.objects.create(user=self.requester, department=neurology)
        Clinician.objects.create(user=self.assignee, department=surgery)
        patient = Patient.objects.create(
            patient_no="P-001",
            name="환자",
            birth_date="1980-01-02",
            estimated_age=46,
            sex="M",
            created_by=self.requester,
        )
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=patient,
            encounter_no="E-001",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.consultation = Consultation.objects.create(
            encounter=encounter,
            consultation_type="NEUROSURGERY",
            requested_by=self.requester,
            assigned_to=self.assignee,
            priority="URGENT",
            reason="검토 요청",
            status="IN_PROGRESS",
            requested_at=now,
            accepted_at=now,
            started_at=now,
            created_at=now,
            updated_at=now,
        )

    def test_list_includes_patient_and_clinician_summaries(self):
        self.client.force_authenticate(self.requester)

        response = self.client.get(reverse("api_con_001_api_con_002"))

        self.assertEqual(response.status_code, 200)
        item = response.json()["results"][0]
        self.assertEqual(item["type"], "NEUROSURGERY")
        self.assertEqual(item["patient_summary"]["patient_no"], "P-001")
        self.assertEqual(item["patient_summary"]["name"], "환자")
        self.assertEqual(item["requested_by"]["name"], "요청의")
        self.assertEqual(item["requested_by"]["department"], "신경과")
        self.assertEqual(item["assigned_to"]["name"], "담당의")
        self.assertEqual(item["assigned_to"]["department"], "신경외과")
        self.assertEqual(item["viewer_relation"], "REQUESTED_BY")
        self.assertEqual(item["allowed_actions"], ["CANCEL"])

    def test_detail_preserves_raw_fields_and_adds_frontend_shape(self):
        self.client.force_authenticate(self.requester)

        response = self.client.get(reverse("api_con_003", args=[self.consultation.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.consultation.id))
        self.assertEqual(payload["consultation_type"], "NEUROSURGERY")
        self.assertEqual(payload["requested_by_id"], str(self.requester.id))
        self.assertEqual(payload["assigned_to_id"], str(self.assignee.id))
        self.assertEqual(payload["consultation_id"], str(self.consultation.id))
        self.assertEqual(payload["type"], "NEUROSURGERY")
        self.assertEqual(payload["patient_summary"]["name"], "환자")
        self.assertEqual(payload["requested_by"]["department"], "신경과")
        self.assertEqual(payload["assigned_to"]["department"], "신경외과")
        self.assertEqual(payload["viewer_relation"], "REQUESTED_BY")
        self.assertEqual(payload["ui_status"], "검토 중")
