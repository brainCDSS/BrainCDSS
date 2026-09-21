from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.clinical_records.models import Encounter
from apps.consultations.models import Consultation, ConsultationMessage
from apps.notifications.models import Notification
from apps.organizations.models import Clinician, Department, Hospital
from apps.patients.models import Patient


class ConsultationListResponseTests(APITestCase):
    def setUp(self):
        neurologist_role = Role.objects.get(code="NEUROLOGIST")
        surgeon_role = Role.objects.get(code="NEUROSURGEON")
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
        self.assertEqual(item["reason"], "검토 요청")

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

    def test_requested_assignee_can_accept_or_reject(self):
        self.consultation.status = "REQUESTED"
        self.consultation.accepted_at = None
        self.consultation.started_at = None
        self.consultation.save(update_fields=["status", "accepted_at", "started_at"])
        self.client.force_authenticate(self.assignee)

        response = self.client.get(reverse("api_con_003", args=[self.consultation.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allowed_actions"], ["ACCEPT", "REJECT"])

    def test_requested_requester_keeps_cancel_action(self):
        self.consultation.status = "REQUESTED"
        self.consultation.accepted_at = None
        self.consultation.started_at = None
        self.consultation.save(update_fields=["status", "accepted_at", "started_at"])
        self.client.force_authenticate(self.requester)

        response = self.client.get(reverse("api_con_003", args=[self.consultation.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allowed_actions"], ["CANCEL"])

    def test_requested_unrelated_clinician_cannot_view_consultation(self):
        unrelated = User.objects.create_user(
            "unrelated",
            "password",
            name="다른 담당의",
            role=self.assignee.role,
        )
        Clinician.objects.create(
            user=unrelated,
            department=Clinician.objects.get(user=self.assignee).department,
        )
        self.consultation.status = "REQUESTED"
        self.consultation.accepted_at = None
        self.consultation.started_at = None
        self.consultation.save(update_fields=["status", "accepted_at", "started_at"])
        self.client.force_authenticate(unrelated)

        response = self.client.get(reverse("api_con_003", args=[self.consultation.id]))

        self.assertEqual(response.status_code, 404)

    def test_start_preserves_requester_and_assignee(self):
        self.consultation.status = "ACCEPTED"
        self.consultation.started_at = None
        self.consultation.save(update_fields=["status", "started_at"])
        self.client.force_authenticate(self.assignee)

        response = self.client.post(
            reverse("api_con_005", args=[self.consultation.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, "IN_PROGRESS")
        self.assertEqual(self.consultation.requested_by_id, self.requester.id)
        self.assertEqual(self.consultation.assigned_to_id, self.assignee.id)

    def test_accept_and_respond_preserve_requester_and_assignee(self):
        self.consultation.status = "REQUESTED"
        self.consultation.accepted_at = None
        self.consultation.started_at = None
        self.consultation.save(update_fields=["status", "accepted_at", "started_at"])
        self.client.force_authenticate(self.assignee)

        accept_response = self.client.post(
            reverse("api_con_004", args=[self.consultation.id]),
            {},
            format="json",
        )

        self.assertEqual(accept_response.status_code, 200)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.requested_by_id, self.requester.id)
        self.assertEqual(self.consultation.assigned_to_id, self.assignee.id)

        self.consultation.status = "IN_PROGRESS"
        self.consultation.save(update_fields=["status"])
        respond_response = self.client.post(
            reverse("api_con_006", args=[self.consultation.id]),
            {"final_opinion": "Consultation response."},
            format="json",
        )

        self.assertEqual(respond_response.status_code, 200)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.requested_by_id, self.requester.id)
        self.assertEqual(self.consultation.assigned_to_id, self.assignee.id)

    def test_neurologist_can_create_consultation(self):
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-002",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            {
                "encounter_id": str(encounter.id),
                "consultation_type": "NEUROSURGERY",
                "assigned_to_id": str(self.assignee.id),
                "priority": "URGENT",
                "reason": "Urgent radiology consultation requested.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "REQUESTED")
        self.assertEqual(
            response.json()["assigned_to_id"],
            str(self.assignee.id),
        )
        self.assertTrue(
            Consultation.objects.filter(
                encounter=encounter,
                consultation_type="NEUROSURGERY",
                requested_by=self.requester,
                assigned_to=self.assignee,
                status="REQUESTED",
            ).exists()
        )
        list_response = self.client.get(reverse("api_con_001_api_con_002"))
        created = next(
            item
            for item in list_response.json()["results"]
            if item["encounter_id"] == str(encounter.id)
        )
        self.assertEqual(created["assigned_to"]["id"], str(self.assignee.id))

    def test_create_requires_assigned_clinician(self):
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-003",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            {
                "encounter_id": str(encounter.id),
                "consultation_type": "NEUROSURGERY",
                "priority": "URGENT",
                "reason": "Assigned clinician is required.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "assigned_to_id",
            response.json()["error"]["details"],
        )

    def test_create_rejects_assignee_from_different_department(self):
        radiology_role = Role.objects.get(code="RADIOLOGY")
        radiologist = User.objects.create_user(
            "radiologist",
            "password",
            name="Radiologist",
            role=radiology_role,
        )
        hospital = Clinician.objects.get(user=self.assignee).department.hospital
        radiology = Department.objects.create(
            hospital=hospital,
            code="RADIOLOGY",
            name="Radiology",
        )
        Clinician.objects.create(user=radiologist, department=radiology)
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-004",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            {
                "encounter_id": str(encounter.id),
                "consultation_type": "NEUROSURGERY",
                "assigned_to_id": str(radiologist.id),
                "priority": "URGENT",
                "reason": "Department must match consultation type.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "assigned_to_id",
            response.json()["error"]["details"],
        )

    def test_neurologist_can_create_assigned_radiology_consultation(self):
        radiology_role = Role.objects.get(code="RADIOLOGY")
        radiologist = User.objects.create_user(
            "radiologist",
            "password",
            name="Radiologist",
            role=radiology_role,
        )
        hospital = Clinician.objects.get(user=self.assignee).department.hospital
        radiology = Department.objects.create(
            hospital=hospital,
            code="RADIOLOGY",
            name="Radiology",
        )
        Clinician.objects.create(user=radiologist, department=radiology)
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-005",
            encounter_type="EMERGENCY",
            status="REGISTERED",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            {
                "encounter_id": str(encounter.id),
                "consultation_type": "RADIOLOGY",
                "assigned_to_id": str(radiologist.id),
                "priority": "ROUTINE",
                "reason": "Radiology consultation requested.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["assigned_to_id"], str(radiologist.id))

    def test_create_rejects_active_duplicate_for_same_assignee(self):
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-006",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        payload = {
            "encounter_id": str(encounter.id),
            "consultation_type": "NEUROSURGERY",
            "assigned_to_id": str(self.assignee.id),
            "priority": "URGENT",
            "reason": "Duplicate consultation check.",
        }
        self.client.force_authenticate(self.requester)
        self.client.post(
            reverse("api_con_001_api_con_002"),
            payload,
            format="json",
        )

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_create_rejects_inactive_encounter(self):
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-007",
            encounter_type="EMERGENCY",
            status="COMPLETED",
            arrived_at=now,
            ended_at=now,
            created_at=now,
            updated_at=now,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            {
                "encounter_id": str(encounter.id),
                "consultation_type": "NEUROSURGERY",
                "assigned_to_id": str(self.assignee.id),
                "priority": "URGENT",
                "reason": "Inactive encounter must be rejected.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_create_notifies_only_assigned_clinician(self):
        other_surgeon = User.objects.create_user(
            "other-surgeon",
            "password",
            name="Other Surgeon",
            role=self.assignee.role,
        )
        surgery = Clinician.objects.get(user=self.assignee).department
        Clinician.objects.create(user=other_surgeon, department=surgery)
        now = timezone.now()
        encounter = Encounter.objects.create(
            patient=self.consultation.encounter.patient,
            encounter_no="E-008",
            encounter_type="EMERGENCY",
            status="IN_PROGRESS",
            arrived_at=now,
            created_at=now,
            updated_at=now,
        )
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("api_con_001_api_con_002"),
            {
                "encounter_id": str(encounter.id),
                "consultation_type": "NEUROSURGERY",
                "assigned_to_id": str(self.assignee.id),
                "priority": "URGENT",
                "reason": "Assigned clinician notification.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        notification = Notification.objects.get(
            recipient_user=self.assignee,
        )
        self.assertEqual(notification.category, "CONSULTATION")
        self.assertEqual(notification.severity, "WARNING")
        self.assertEqual(
            notification.data_json["consultation_id"],
            response.json()["consultation_id"],
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient_user=other_surgeon,
            ).exists()
        )

    def test_consultation_participants_can_exchange_messages(self):
        self.client.force_authenticate(self.requester)
        url = reverse("consultation_messages", args=[self.consultation.id])

        create_response = self.client.post(
            url,
            {"content": "Please confirm the lesion location."},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertTrue(create_response.json()["is_mine"])
        self.assertEqual(create_response.json()["sender"]["name"], self.requester.name)
        self.assertEqual(
            ConsultationMessage.objects.get().content,
            "Please confirm the lesion location.",
        )

        self.client.force_authenticate(self.assignee)
        list_response = self.client.get(url)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["results"]), 1)
        self.assertFalse(list_response.json()["results"][0]["is_mine"])

    def test_consultation_messages_support_incremental_cursor(self):
        self.client.force_authenticate(self.requester)
        url = reverse("consultation_messages", args=[self.consultation.id])
        first = self.client.post(
            url,
            {"content": "First message"},
            format="json",
        ).json()
        second = self.client.post(
            url,
            {"content": "Second message"},
            format="json",
        ).json()

        response = self.client.get(url, {"after": first["message_id"]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["message_id"] for item in response.json()["results"]],
            [second["message_id"]],
        )
        self.assertEqual(response.json()["next_cursor"], second["message_id"])

    def test_unrelated_clinician_cannot_access_consultation_messages(self):
        unrelated = User.objects.create_user(
            "chat-outsider",
            "password",
            name="Chat Outsider",
            role=self.assignee.role,
        )
        self.client.force_authenticate(unrelated)
        url = reverse("consultation_messages", args=[self.consultation.id])

        list_response = self.client.get(url)
        create_response = self.client.post(
            url,
            {"content": "This must not be saved."},
            format="json",
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)
        self.assertFalse(ConsultationMessage.objects.exists())

    def test_closed_consultation_messages_are_read_only(self):
        self.consultation.status = "CLOSED"
        self.consultation.save(update_fields=["status"])
        self.client.force_authenticate(self.requester)

        response = self.client.post(
            reverse("consultation_messages", args=[self.consultation.id]),
            {"content": "Too late"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(ConsultationMessage.objects.exists())

    def test_consultation_message_validates_content(self):
        self.client.force_authenticate(self.requester)
        url = reverse("consultation_messages", args=[self.consultation.id])

        empty_response = self.client.post(url, {"content": "   "}, format="json")
        long_response = self.client.post(
            url,
            {"content": "x" * 2001},
            format="json",
        )

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(long_response.status_code, 400)
        self.assertFalse(ConsultationMessage.objects.exists())

    def test_requested_assigned_radiologist_can_accept_or_reject(self):
        radiology_role = Role.objects.get(code="RADIOLOGY")

        radiologist = User.objects.create_user(
            "workflow-radiologist",
            "password",
            name="영상의학과 테스트의",
            role=radiology_role,
        )

        hospital = Clinician.objects.get(
            user=self.assignee,
        ).department.hospital

        radiology = Department.objects.create(
            hospital=hospital,
            code="FT-RAD",
            name="영상의학과",
        )

        Clinician.objects.create(
            user=radiologist,
            department=radiology,
        )

        now = timezone.now()

        consultation = Consultation.objects.create(
            encounter=self.consultation.encounter,
            consultation_type="RADIOLOGY",
            requested_by=self.requester,
            assigned_to=radiologist,
            priority="URGENT",
            reason="영상 판독 협진 요청",
            status="REQUESTED",
            requested_at=now,
            created_at=now,
            updated_at=now,
        )

        self.client.force_authenticate(radiologist)

        response = self.client.get(
            reverse(
                "api_con_003",
                args=[consultation.id],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.json()["allowed_actions"],
            ["ACCEPT", "REJECT"],
        )


    def test_can_create_new_consultation_when_previous_one_is_in_progress(self):
        self.assertEqual(
            self.consultation.status,
            "IN_PROGRESS",
        )

        self.client.force_authenticate(
            self.requester,
        )

        response = self.client.post(
            reverse(
                "api_con_001_api_con_002"
            ),
            {
                "encounter_id": str(
                    self.consultation.encounter_id
                ),
                "consultation_type": "NEUROSURGERY",
                "assigned_to_id": str(
                    self.assignee.id
                ),
                "priority": "STAT",
                "reason": "진행 중 협진과 별개의 추가 협진 요청",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            Consultation.objects.filter(
                encounter_id=
                    self.consultation.encounter_id,
                consultation_type=
                    "NEUROSURGERY",
                assigned_to_id=
                    self.assignee.id,
            ).count(),
            2,
        )
