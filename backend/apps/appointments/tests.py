"""Tests for appointment-specific API response formatting."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from django.utils import timezone as django_timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Permission, Role, RolePermission, User
from apps.appointments.api.generated_real_149 import ContractView012
from apps.appointments.api.views import AppointmentCorrectView
from apps.appointments.models import (
    Appointment,
    AppointmentSlot,
    AppointmentStatusHistory,
)
from apps.common.remaining149_runtime import _appointment_payload
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


class StaffAppointmentResponseTests(TestCase):
    def setUp(self):
        role = Role.objects.get(code="NURSE")
        permission = Permission.objects.create(
            code="appointment.read.staff",
            name="예약 업무 조회",
            domain="appointments",
        )
        RolePermission.objects.create(
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
        permission = Permission.objects.create(
            code="appointment.correct",
            name="Correct appointment status",
            domain="appointments",
        )
        RolePermission.objects.create(role=role, permission=permission)
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
