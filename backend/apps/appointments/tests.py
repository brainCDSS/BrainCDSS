"""Tests for appointment-specific API response formatting."""

from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone as django_timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Permission, Role, RolePermission, User
from apps.appointments.api.generated_real_149 import (
    ContractView000,
    ContractView001,
    ContractView002,
    ContractView007,
    ContractView008,
    ContractView012,
)
from apps.appointments.api.views import (
    AppointmentCorrectView,
    StaffAppointmentCreateView,
)
from apps.assistant.api.internal_mcp import AppointmentsInternalView
from apps.appointments.models import (
    Appointment,
    AppointmentRescheduleHistory,
    AppointmentSlot,
    AppointmentStatusHistory,
    ClinicianSchedule,
)
from apps.common.remaining149_runtime import _appointment_payload
from apps.common.models import OutboxEvent
from apps.notifications.models import Notification
from apps.organizations.models import Clinician, Department, Hospital
from apps.patients.models import Patient


class AppointmentPayloadTests(SimpleTestCase):
    def test_related_names_are_returned_with_their_ids(self):
        patient_id = uuid4()
        department_id = uuid4()
        clinician_id = uuid4()
        slot_id = uuid4()

        appointment = SimpleNamespace(
            id=uuid4(),
            patient_id=patient_id,
            patient=SimpleNamespace(
                patient_no="TEST-PATIENT-001",
                name="테스트 환자",
            ),
            hospital_id=uuid4(),
            hospital=SimpleNamespace(name="테스트 병원"),
            department_id=department_id,
            department=SimpleNamespace(name="신경과"),
            clinician_id=clinician_id,
            clinician=SimpleNamespace(
                id=clinician_id,
                user=SimpleNamespace(name="테스트 담당의"),
            ),
            slot=SimpleNamespace(
                id=slot_id,
                start_at=datetime(2026, 9, 11, 9, tzinfo=timezone.utc),
                end_at=datetime(2026, 9, 11, 9, 30, tzinfo=timezone.utc),
                status="BOOKED",
                held_until=None,
            ),
            requested_slot=None,
            handled_by=None,
            status="CONFIRMED",
            request_type="NEW",
            rejection_reason=None,
            cancel_reason=None,
            requested_at=datetime(2026, 9, 10, 9, tzinfo=timezone.utc),
            reschedule_requested_at=None,
            confirmed_at=datetime(2026, 9, 10, 10, tzinfo=timezone.utc),
            cancelled_at=None,
            completed_at=None,
        )

        payload = _appointment_payload(appointment)

        self.assertEqual(payload["patient"]["id"], str(patient_id))
        self.assertEqual(payload["patient"]["name"], "테스트 환자")
        self.assertEqual(payload["department"]["id"], str(department_id))
        self.assertEqual(payload["department"]["name"], "신경과")
        self.assertEqual(payload["clinician"]["id"], str(clinician_id))
        self.assertEqual(payload["clinician"]["name"], "테스트 담당의")
        self.assertEqual(payload["slot"]["id"], str(slot_id))
        self.assertNotIn("patient_id", payload)
        self.assertNotIn("department_id", payload)
        self.assertNotIn("clinician_id", payload)
        self.assertEqual(payload["reschedule_history"], [])


class AppointmentRescheduleHistoryTests(TestCase):
    def setUp(self):
        self.patient_role, _ = Role.objects.get_or_create(
            code="PATIENT",
            defaults={"name": "Patient"},
        )
        self.nurse_role, _ = Role.objects.get_or_create(
            code="NURSE",
            defaults={"name": "Nurse"},
        )
        clinician_role, _ = Role.objects.get_or_create(
            code="NEUROLOGIST",
            defaults={"name": "Clinician"},
        )
        read_permission, _ = Permission.objects.get_or_create(
            code="appointment.read.own",
            defaults={
                "name": "Read own appointments",
                "domain": "appointments",
            },
        )
        accept_permission, _ = Permission.objects.get_or_create(
            code="appointment.accept",
            defaults={
                "name": "Accept appointments",
                "domain": "appointments",
            },
        )
        RolePermission.objects.get_or_create(
            role=self.patient_role,
            permission=read_permission,
        )
        RolePermission.objects.get_or_create(
            role=self.nurse_role,
            permission=accept_permission,
        )
        self.patient_user = User.objects.create_user(
            login_id="reschedule-history-patient",
            password="test-password",
            name="Patient",
            role=self.patient_role,
        )
        self.nurse_user = User.objects.create_user(
            login_id="reschedule-history-nurse",
            password="test-password",
            name="Nurse",
            role=self.nurse_role,
        )
        clinician_user = User.objects.create_user(
            login_id="reschedule-history-clinician",
            password="test-password",
            name="Clinician",
            role=clinician_role,
        )
        hospital = Hospital.objects.create(
            name="Reschedule History Hospital",
            address="Appointment Address",
        )
        department = Department.objects.create(
            hospital=hospital,
            code="RESCHEDULE-HISTORY",
            name="Appointment Department",
        )
        clinician = Clinician.objects.create(
            user=clinician_user,
            department=department,
        )
        patient = Patient.objects.create(
            user=self.patient_user,
            patient_no="RESCHEDULE-HISTORY-PATIENT",
            name="Patient",
            created_by=clinician_user,
        )
        start_at = django_timezone.make_aware(
            datetime.combine(date.today() + timedelta(days=1), time(9)),
        )
        self.previous_slot = AppointmentSlot.objects.create(
            clinician=clinician,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=30),
            status="BOOKED",
        )
        self.changed_slot = AppointmentSlot.objects.create(
            clinician=clinician,
            start_at=start_at + timedelta(hours=1),
            end_at=start_at + timedelta(hours=1, minutes=30),
            status="HELD",
            held_until=django_timezone.now() + timedelta(minutes=10),
        )
        self.appointment = Appointment.objects.create(
            patient=patient,
            hospital=hospital,
            department=department,
            clinician=clinician,
            slot=self.previous_slot,
            requested_slot=self.changed_slot,
            status="CONFIRMED",
            request_type="RESCHEDULE",
            requested_at=django_timezone.now(),
            reschedule_requested_at=django_timezone.now(),
            confirmed_at=django_timezone.now(),
        )

    def test_accepting_reschedule_preserves_history_for_patient_detail(self):
        accept_request = APIRequestFactory().post(
            f"/api/v1/appointments/{self.appointment.id}/accept",
            {"memo": "Requested schedule change approved"},
            format="json",
        )
        force_authenticate(accept_request, user=self.nurse_user)

        response = ContractView002.as_view()(
            accept_request,
            appointment_id=self.appointment.id,
        )

        self.assertEqual(response.status_code, 200)
        history = AppointmentRescheduleHistory.objects.get(
            appointment=self.appointment,
        )
        self.assertEqual(history.previous_slot_id, self.previous_slot.id)
        self.assertEqual(history.changed_slot_id, self.changed_slot.id)
        self.assertEqual(
            history.reschedule_reason,
            "Requested schedule change approved",
        )
        self.assertEqual(history.changed_by_id, self.nurse_user.id)

        detail_request = APIRequestFactory().get(
            f"/api/v1/appointments/{self.appointment.id}",
        )
        force_authenticate(detail_request, user=self.patient_user)
        detail_response = ContractView001.as_view()(
            detail_request,
            appointment_id=self.appointment.id,
        )

        self.assertEqual(detail_response.status_code, 200)
        payload = detail_response.data["reschedule_history"]
        self.assertEqual(len(payload), 1)
        self.assertEqual(
            payload[0]["previous_slot"]["id"],
            str(self.previous_slot.id),
        )
        self.assertEqual(
            payload[0]["changed_slot"]["id"],
            str(self.changed_slot.id),
        )
        self.assertEqual(
            payload[0]["reschedule_reason"],
            "Requested schedule change approved",
        )
        self.assertIsNotNone(payload[0]["rescheduled_at"])

        list_request = APIRequestFactory().get("/api/v1/appointments")
        force_authenticate(list_request, user=self.patient_user)
        list_response = ContractView000.as_view()(list_request)

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.data["results"][0]["reschedule_history"][0]
            ["previous_slot"]["id"],
            str(self.previous_slot.id),
        )


class AppointmentCreateSlotResolutionTests(TestCase):
    def setUp(self):
        self.patient_role = Role.objects.get(code="PATIENT")
        self.clinician_role = Role.objects.get(
            code="NEUROLOGIST",
        )
        self.request_permission, _ = Permission.objects.get_or_create(
            code="appointment.request",
            defaults={"name": "Request appointment", "domain": "appointments"},
        )
        self.read_permission, _ = Permission.objects.get_or_create(
            code="appointment.read.own",
            defaults={"name": "Read own appointments", "domain": "appointments"},
        )
        RolePermission.objects.get_or_create(
            role=self.patient_role,
            permission=self.request_permission,
        )
        RolePermission.objects.get_or_create(
            role=self.patient_role,
            permission=self.read_permission,
        )
        self.patient_user = User.objects.create_user(
            login_id="appointment-slot-patient",
            password="test-password",
            name="Patient",
            role=self.patient_role,
        )
        clinician_user = User.objects.create_user(
            login_id="appointment-slot-clinician",
            password="test-password",
            name="Clinician",
            role=self.clinician_role,
        )
        self.hospital = Hospital.objects.create(
            name="Appointment Hospital",
            address="Appointment Address",
        )
        self.department = Department.objects.create(
            hospital=self.hospital,
            code="APPOINTMENT-TEST",
            name="Appointment Department",
        )
        self.clinician = Clinician.objects.create(
            user=clinician_user,
            department=self.department,
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            patient_no="APPOINTMENT-SLOT-PATIENT",
            name="Patient",
            created_by=clinician_user,
        )
        self.start_at = django_timezone.make_aware(
            datetime.combine(date.today() + timedelta(days=1), time(9)),
        )
        self.schedule = ClinicianSchedule.objects.create(
            clinician=self.clinician,
            weekday=self.start_at.weekday(),
            start_time=time(9),
            end_time=time(18, 30),
            slot_minutes=30,
            effective_from=self.start_at.date(),
            is_active=True,
        )

    def _create(self, start_at):
        request = APIRequestFactory().post(
            "/api/v1/appointments",
            {
                "clinician_id": str(self.clinician.id),
                "start_at": start_at.isoformat(),
            },
            format="json",
        )
        force_authenticate(request, user=self.patient_user)
        return ContractView000.as_view()(request)

    def test_creates_and_connects_slot_for_selected_time(self):
        response = self._create(self.start_at)

        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(pk=response.data["appointment_id"])
        self.assertIsNotNone(appointment.slot_id)
        self.assertEqual(appointment.slot.start_at, self.start_at)
        self.assertEqual(
            datetime.fromisoformat(response.data["scheduled_at"]),
            self.start_at,
        )
        self.assertEqual(
            datetime.fromisoformat(response.data["start_at"]),
            self.start_at,
        )
        self.assertEqual(
            datetime.fromisoformat(response.data["end_at"]),
            self.start_at + timedelta(minutes=30),
        )
        list_request = APIRequestFactory().get("/api/v1/appointments")
        force_authenticate(list_request, user=self.patient_user)
        list_response = ContractView000.as_view()(list_request)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            datetime.fromisoformat(
                list_response.data["results"][0]["scheduled_at"],
            ),
            self.start_at,
        )

    def test_allows_eighteen_hundred_when_the_schedule_duration_fits(self):
        start_at = django_timezone.make_aware(
            datetime.combine(self.start_at.date(), time(18)),
        )

        response = self._create(start_at)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            datetime.fromisoformat(response.data["start_at"]),
            start_at,
        )
        self.assertEqual(
            datetime.fromisoformat(response.data["end_at"]),
            start_at + timedelta(minutes=30),
        )

    def test_reuses_existing_slot_for_selected_time(self):
        slot = AppointmentSlot.objects.create(
            clinician=self.clinician,
            schedule=self.schedule,
            start_at=self.start_at,
            end_at=self.start_at + timedelta(minutes=30),
            status="AVAILABLE",
        )

        response = self._create(self.start_at)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["slot"]["id"], str(slot.id))
        self.assertEqual(
            AppointmentSlot.objects.filter(
                clinician=self.clinician,
                start_at=self.start_at,
            ).count(),
            1,
        )

    def test_rejects_times_outside_the_booking_window(self):
        for selected_time in (time(8, 30), time(18, 30)):
            start_at = django_timezone.make_aware(
                datetime.combine(self.start_at.date(), selected_time),
            )
            response = self._create(start_at)

            self.assertEqual(response.status_code, 400)
            self.assertEqual(Appointment.objects.count(), 0)


class AppointmentAvailableSlotGenerationTests(TestCase):
    def setUp(self):
        patient_role = Role.objects.get(code="PATIENT")
        clinician_role = Role.objects.get(
            code="NEUROLOGIST",
        )
        self.patient_user = User.objects.create_user(
            login_id="available-slot-patient",
            password="test-password",
            name="Patient",
            role=patient_role,
        )
        clinician_user = User.objects.create_user(
            login_id="available-slot-clinician",
            password="test-password",
            name="Clinician",
            role=clinician_role,
        )
        hospital = Hospital.objects.create(
            name="Available Slot Hospital",
            address="Available Slot Address",
        )
        department = Department.objects.create(
            hospital=hospital,
            code="AVAILABLE-SLOT-TEST",
            name="Available Slot Department",
        )
        self.clinician = Clinician.objects.create(
            user=clinician_user,
            department=department,
        )
        self.target_date = date.today() + timedelta(days=1)
        ClinicianSchedule.objects.create(
            clinician=self.clinician,
            weekday=self.target_date.weekday(),
            start_time=time(9),
            end_time=time(11),
            slot_minutes=30,
            effective_from=self.target_date,
            is_active=True,
        )

    def _list_slots(self):
        request = APIRequestFactory().get(
            "/api/v1/clinicians/{}/slots?date={}".format(
                self.clinician.id,
                self.target_date.isoformat(),
            ),
        )
        force_authenticate(request, user=self.patient_user)
        return ContractView008.as_view()(request, clinician_id=self.clinician.id)

    def test_creates_schedule_slots_once_and_returns_them_in_order(self):
        response = self._list_slots()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [
                datetime.fromisoformat(item["start_at"]).astimezone(
                    django_timezone.get_current_timezone(),
                ).time()
                for item in response.data["slots"]
            ],
            [time(9), time(9, 30), time(10), time(10, 30)],
        )
        self.assertEqual(AppointmentSlot.objects.count(), 4)

        repeat_response = self._list_slots()

        self.assertEqual(repeat_response.status_code, 200)
        self.assertEqual(len(repeat_response.data["slots"]), 4)
        self.assertEqual(AppointmentSlot.objects.count(), 4)

    def test_excludes_booked_slots_without_creating_duplicates(self):
        self._list_slots()
        booked_slot = AppointmentSlot.objects.order_by("start_at").first()
        booked_slot.status = "BOOKED"
        booked_slot.save(update_fields=["status"])

        response = self._list_slots()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["slots"]), 3)
        self.assertNotIn(
            str(booked_slot.id),
            [item["id"] for item in response.data["slots"]],
        )
        self.assertEqual(AppointmentSlot.objects.count(), 4)

    def test_schedule_endpoint_returns_only_the_requested_clinician_rules(self):
        nurse_role = Role.objects.get(code="NURSE")
        permission, _ = Permission.objects.get_or_create(
            code="schedule.read",
            defaults={"name": "Schedule read", "domain": "schedule"},
        )
        RolePermission.objects.get_or_create(role=nurse_role, permission=permission)
        nurse = User.objects.create_user(
            login_id="schedule-read-nurse",
            password="test-password",
            name="Nurse",
            role=nurse_role,
        )
        other_user = User.objects.create_user(
            login_id="other-schedule-clinician",
            password="test-password",
            name="Other clinician",
            role=Role.objects.get(code="NEUROLOGIST"),
        )
        other_clinician = Clinician.objects.create(
            user=other_user,
            department=self.clinician.department,
        )
        ClinicianSchedule.objects.create(
            clinician=other_clinician,
            weekday=self.target_date.weekday(),
            start_time=time(8),
            end_time=time(12),
            slot_minutes=30,
            effective_from=self.target_date,
            is_active=True,
        )
        request = APIRequestFactory().get(
            "/api/v1/clinicians/{}/schedule".format(self.clinician.id),
        )
        force_authenticate(request, user=nurse)

        response = ContractView007.as_view()(
            request,
            clinician_id=self.clinician.id,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["rules"]), 1)
        self.assertEqual(
            response.data["rules"][0]["clinician_id"],
            str(self.clinician.id),
        )
        self.assertEqual(response.data["rules"][0]["start_time"], "09:00:00")

    def test_clinician_can_save_only_own_schedule(self):
        clinician_role = Role.objects.get(code="NEUROLOGIST")
        permission, _ = Permission.objects.get_or_create(
            code="schedule.manage",
            defaults={"name": "Schedule manage", "domain": "schedule"},
        )
        RolePermission.objects.get_or_create(
            role=clinician_role,
            permission=permission,
        )
        request = APIRequestFactory().put(
            "/api/v1/clinicians/{}/schedule".format(self.clinician.id),
            {
                "schedules": [
                    {
                        "weekday": self.target_date.weekday(),
                        "start_time": "09:00",
                        "end_time": "18:00",
                        "slot_minutes": 15,
                        "effective_from": self.target_date.isoformat(),
                        "effective_to": None,
                        "is_active": True,
                    }
                ]
            },
            format="json",
        )
        force_authenticate(request, user=self.clinician.user)

        response = ContractView007.as_view()(
            request,
            clinician_id=self.clinician.id,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rules"][0]["end_time"], "18:00:00")
        self.assertEqual(response.data["rules"][0]["slot_minutes"], 15)


class StaffAppointmentCreateTests(TestCase):
    def setUp(self):
        nurse_role = Role.objects.get(code="NURSE")
        patient_role = Role.objects.get(code="PATIENT")
        clinician_role = Role.objects.get(code="NEUROLOGIST")
        permission, _ = Permission.objects.get_or_create(
            code="appointment.read.staff",
            defaults={"name": "Staff appointment access", "domain": "appointments"},
        )
        RolePermission.objects.get_or_create(
            role=nurse_role,
            permission=permission,
        )
        self.nurse = User.objects.create_user(
            login_id="staff-booking-nurse",
            password="test-password",
            name="Booking Nurse",
            role=nurse_role,
        )
        self.patient_user = User.objects.create_user(
            login_id="staff-booking-patient",
            password="test-password",
            name="Booking Patient",
            role=patient_role,
        )
        clinician_user = User.objects.create_user(
            login_id="staff-booking-clinician",
            password="test-password",
            name="Booking Clinician",
            role=clinician_role,
        )
        hospital = Hospital.objects.create(
            name="Staff Booking Hospital",
            address="Staff Booking Address",
        )
        department = Department.objects.create(
            hospital=hospital,
            code="STAFF-BOOKING",
            name="Staff Booking Department",
        )
        clinician = Clinician.objects.create(
            user=clinician_user,
            department=department,
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            patient_no="STAFF-BOOKING-PATIENT",
            name="Booking Patient",
            created_by=self.nurse,
        )
        start_at = django_timezone.now() + timedelta(days=1)
        self.slot = AppointmentSlot.objects.create(
            clinician=clinician,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=30),
            status="AVAILABLE",
        )

    def _create(self):
        request = APIRequestFactory().post(
            "/api/v1/staff/appointment-bookings",
            {"patient_id": str(self.patient.id), "slot_id": str(self.slot.id)},
            format="json",
        )
        force_authenticate(request, user=self.nurse)
        return StaffAppointmentCreateView.as_view()(request)

    @patch("apps.notifications.signals.send_notification_fcm.delay")
    def test_creates_confirmed_relations_notification_outbox_and_fcm(self, fcm_delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self._create()

        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.select_related(
            "patient", "clinician", "department", "hospital", "slot", "handled_by",
        ).get(pk=response.data["appointment_id"])
        self.slot.refresh_from_db()
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.clinician, self.slot.clinician)
        self.assertEqual(appointment.department, self.slot.clinician.department)
        self.assertEqual(appointment.hospital, self.slot.clinician.department.hospital)
        self.assertEqual(appointment.handled_by, self.nurse)
        self.assertEqual(appointment.status, "CONFIRMED")
        self.assertEqual(self.slot.status, "BOOKED")

        notification = Notification.objects.get(
            recipient_user=self.patient_user,
            category="APPOINTMENT",
        )
        self.assertEqual(notification.data_json["event_type"], "APPOINTMENT_CONFIRMED")
        self.assertEqual(notification.data_json["resource_id"], str(appointment.id))
        self.assertEqual(notification.data_json["clinician_id"], str(appointment.clinician_id))
        fcm_delay.assert_called_once_with(str(notification.id))

        event = OutboxEvent.objects.get(
            event_type="appointment.confirmed.v1",
            aggregate=str(appointment.id),
        )
        self.assertEqual(event.payload["patient"]["id"], str(self.patient.id))
        self.assertEqual(event.status, "PENDING")

    @override_settings(MCP_BACKEND_TOKEN="appointment-mcp-test-token")
    def test_created_appointment_is_visible_to_patient_and_read_only_mcp(self):
        response = self._create()
        appointment_id = response.data["appointment_id"]

        patient_request = APIRequestFactory().get("/api/v1/appointments")
        force_authenticate(patient_request, user=self.patient_user)
        patient_response = ContractView000.as_view()(patient_request)
        self.assertEqual(patient_response.status_code, 200)
        self.assertEqual(patient_response.data["results"][0]["appointment_id"], appointment_id)

        mcp_request = APIRequestFactory().get(
            "/internal/v1/mcp/get_appointments/",
            {"patient_id": str(self.patient.id)},
            HTTP_AUTHORIZATION="Bearer appointment-mcp-test-token",
        )
        mcp_response = AppointmentsInternalView.as_view()(mcp_request)
        self.assertEqual(mcp_response.status_code, 200)
        self.assertEqual(mcp_response.data["data"]["items"][0]["id"], appointment_id)
        self.assertEqual(mcp_response.data["data"]["items"][0]["status"], "CONFIRMED")

    def test_rejects_second_booking_for_the_same_slot(self):
        self.assertEqual(self._create().status_code, 201)
        response = self._create()
        self.assertEqual(response.status_code, 409)
        self.assertIn("SLOT_NOT_AVAILABLE", str(response.data))
        self.assertEqual(Appointment.objects.count(), 1)


class StaffAppointmentResponseTests(TestCase):
    def setUp(self):
        role = Role.objects.get(code="NURSE")
        permission, _ = Permission.objects.get_or_create(
            code="appointment.read.staff",
            defaults={"name": "예약 업무 조회", "domain": "appointments"},
        )
        RolePermission.objects.get_or_create(
            role=role,
            permission=permission,
        )
        self.user = User.objects.create_user(
            login_id="appointment-test-nurse",
            password="test-password",
            name="테스트 간호사",
            role=role,
        )
        clinician_user = User.objects.create_user(
            login_id="appointment-test-clinician",
            password="test-password",
            name="테스트 담당의",
            role=role,
        )
        hospital = Hospital.objects.create(
            name="테스트 병원",
            address="테스트 주소",
        )
        department = Department.objects.create(
            hospital=hospital,
            code="NEUROLOGY-TEST",
            name="신경과",
        )
        clinician = Clinician.objects.create(
            user=clinician_user,
            department=department,
        )
        patient = Patient.objects.create(
            patient_no="TEST-PATIENT-001",
            name="테스트 환자",
            created_by=self.user,
        )
        start_at = django_timezone.now() + timedelta(days=1)
        slot = AppointmentSlot.objects.create(
            clinician=clinician,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=30),
            status="BOOKED",
        )
        self.appointment = Appointment.objects.create(
            patient=patient,
            hospital=hospital,
            department=department,
            clinician=clinician,
            slot=slot,
            status="REJECTED",
        )

    def test_staff_list_returns_names_in_nested_objects(self):
        request = APIRequestFactory().get(
            "/api/v1/staff/appointments",
        )
        force_authenticate(request, user=self.user)

        response = ContractView012.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["appointments"]), 1)
        item = response.data["appointments"][0]
        self.assertEqual(
            item["appointment_id"],
            str(self.appointment.id),
        )
        self.assertEqual(item["patient"]["name"], "테스트 환자")
        self.assertEqual(item["patient"]["patient_no"], "TEST-PATIENT-001")
        self.assertEqual(item["department"]["name"], "신경과")
        self.assertEqual(item["clinician"]["name"], "테스트 담당의")
        self.assertNotIn("patient_id", item)
        self.assertNotIn("department_id", item)
        self.assertNotIn("clinician_id", item)


class AppointmentCorrectionTests(TestCase):
    def setUp(self):
        role = Role.objects.get(code="NURSE")
        permission, _ = Permission.objects.get_or_create(
            code="appointment.correct",
            defaults={"name": "Correct appointment status", "domain": "appointments"},
        )
        RolePermission.objects.get_or_create(role=role, permission=permission)
        self.user = User.objects.create_user(
            login_id="appointment-correction-nurse",
            password="test-password",
            name="Correction Nurse",
            role=role,
        )
        clinician_user = User.objects.create_user(
            login_id="appointment-correction-clinician",
            password="test-password",
            name="Correction Clinician",
            role=role,
        )
        self.hospital = Hospital.objects.create(
            name="Correction Hospital",
            address="Correction Address",
        )
        self.department = Department.objects.create(
            hospital=self.hospital,
            code="CORRECTION-NEUROLOGY",
            name="Neurology",
        )
        self.clinician = Clinician.objects.create(
            user=clinician_user,
            department=self.department,
        )
        self.patient = Patient.objects.create(
            patient_no="CORRECTION-PATIENT-001",
            name="Correction Patient",
            created_by=self.user,
        )

    def _appointment(self, status, slot_status):
        start_at = django_timezone.now() + timedelta(days=1)
        slot = AppointmentSlot.objects.create(
            clinician=self.clinician,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=30),
            status=slot_status,
        )
        appointment = Appointment.objects.create(
            patient=self.patient,
            hospital=self.hospital,
            department=self.department,
            clinician=self.clinician,
            slot=slot,
            status=status,
            rejection_reason="Incorrect rejection" if status == "REJECTED" else None,
            confirmed_at=(
                django_timezone.now() if status == "CONFIRMED" else None
            ),
            handled_by=self.user,
        )
        return appointment, slot

    def _correct(self, appointment, payload):
        request = APIRequestFactory().post(
            f"/api/v1/appointments/{appointment.id}/correct",
            payload,
            format="json",
        )
        force_authenticate(request, user=self.user)
        return AppointmentCorrectView.as_view()(
            request,
            appointment_id=appointment.id,
        )

    def test_rejected_appointment_is_corrected_to_requested(self):
        appointment, slot = self._appointment("REJECTED", "AVAILABLE")
        before = django_timezone.now()

        response = self._correct(appointment, {
            "target_status": "REQUESTED",
            "reason": "Wrong rejection",
        })

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(appointment.status, "REQUESTED")
        self.assertIsNone(appointment.rejection_reason)
        self.assertIsNone(appointment.handled_by)
        self.assertEqual(slot.status, "HELD")
        self.assertGreater(slot.held_until, before + timedelta(minutes=9))
        self.assertTrue(AppointmentStatusHistory.objects.filter(
            appointment=appointment,
            from_status="REJECTED",
            to_status="REQUESTED",
            changed_by=self.user,
            reason="Wrong rejection",
        ).exists())

    def test_confirmed_appointment_is_corrected_to_requested(self):
        appointment, slot = self._appointment("CONFIRMED", "BOOKED")

        response = self._correct(appointment, {
            "target_status": "REQUESTED",
            "reason": "Wrong confirmation",
        })

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(appointment.status, "REQUESTED")
        self.assertIsNone(appointment.confirmed_at)
        self.assertIsNone(appointment.handled_by)
        self.assertEqual(slot.status, "HELD")
        self.assertTrue(AppointmentStatusHistory.objects.filter(
            appointment=appointment,
            from_status="CONFIRMED",
            to_status="REQUESTED",
            reason="Wrong confirmation",
        ).exists())

    def test_reason_is_required(self):
        appointment, slot = self._appointment("REJECTED", "AVAILABLE")

        response = self._correct(appointment, {
            "target_status": "REQUESTED",
            "reason": "",
        })

        self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(appointment.status, "REJECTED")
        self.assertEqual(slot.status, "AVAILABLE")

    def test_role_without_access_is_forbidden(self):
        patient_role = Role.objects.get(code="PATIENT")
        unauthorized_user = User.objects.create_user(
            login_id="appointment-correction-patient",
            password="test-password",
            name="Unauthorized Patient",
            role=patient_role,
        )
        appointment, slot = self._appointment("REJECTED", "AVAILABLE")
        request = APIRequestFactory().post(
            f"/api/v1/appointments/{appointment.id}/correct",
            {
                "target_status": "REQUESTED",
                "reason": "Unauthorized correction",
            },
            format="json",
        )
        force_authenticate(request, user=unauthorized_user)

        response = AppointmentCorrectView.as_view()(
            request,
            appointment_id=appointment.id,
        )

        self.assertEqual(response.status_code, 403)
        appointment.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(appointment.status, "REJECTED")
        self.assertEqual(slot.status, "AVAILABLE")

    def test_invalid_appointment_status_returns_conflict(self):
        appointment, slot = self._appointment("CANCELLED", "AVAILABLE")

        response = self._correct(appointment, {
            "target_status": "REQUESTED",
            "reason": "Invalid state correction",
        })

        self.assertEqual(response.status_code, 409)
        appointment.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(appointment.status, "CANCELLED")
        self.assertEqual(slot.status, "AVAILABLE")

    def test_invalid_slot_status_returns_conflict(self):
        appointment, slot = self._appointment("REJECTED", "BOOKED")

        response = self._correct(appointment, {
            "target_status": "REQUESTED",
            "reason": "Invalid slot correction",
        })

        self.assertEqual(response.status_code, 409)
        appointment.refresh_from_db()
        slot.refresh_from_db()
        self.assertEqual(appointment.status, "REJECTED")
        self.assertEqual(slot.status, "BOOKED")
