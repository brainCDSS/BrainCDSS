import json
from unittest.mock import patch

from django.test import TestCase
from firebase_admin import messaging

from rest_framework.test import APIClient

from apps.accounts.models import Permission, Role, RolePermission, User
from apps.notifications.models import FCMDeviceToken, Notification, NotificationCategoryPreference
from apps.notifications.services.notifications import create_notification_for_user
from apps.notifications.tasks.fcm import (
    _safe_push_text,
    send_notification_device_fcm,
    send_notification_fcm,
)


class NotificationCreationPreferenceTests(TestCase):
    def setUp(self):
        role = Role.objects.get(code="NEUROLOGIST")
        self.user = User.objects.create_user(
            "notification-helper-user", "password", name="Notification user", role=role
        )

    def test_disabled_category_blocks_ordinary_notification(self):
        NotificationCategoryPreference.objects.create(
            user=self.user, category="CONSULTATION", enabled=False
        )

        notification = create_notification_for_user(
            recipient_user=self.user, category="CONSULTATION", severity="INFO",
            title="title", body="body",
        )

        self.assertIsNone(notification)

    def test_critical_notification_bypasses_disabled_preference(self):
        NotificationCategoryPreference.objects.create(
            user=self.user, category="CONSULTATION", enabled=False
        )

        notification = create_notification_for_user(
            recipient_user=self.user, category="CONSULTATION", severity="CRITICAL",
            title="title", body="body",
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient_user, self.user)

    def test_missing_recipient_does_not_create_notification(self):
        self.assertIsNone(create_notification_for_user(
            recipient_user=None, category="CONSULTATION", severity="INFO",
            title="title", body="body",
        ))


class NotificationRuntimeApiTests(TestCase):
    def setUp(self):
        self.role = Role.objects.get(code="NEUROLOGIST")
        self.user = User.objects.create_user(
            "notification-api-user", "password", name="Notification API user", role=self.role
        )
        self.other = User.objects.create_user(
            "notification-api-other", "password", name="Other user", role=self.role
        )
        permission, _ = Permission.objects.get_or_create(
            code="fcm.manage", defaults={"name": "FCM manage", "domain": "notification"}
        )
        RolePermission.objects.get_or_create(role=self.role, permission=permission)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_and_read_are_recipient_scoped_and_read_is_idempotent(self):
        mine = Notification.objects.create(
            recipient_user=self.user, category="CONSULTATION", severity="INFO",
            title="Mine", body="Mine", data_json={},
        )
        Notification.objects.create(
            recipient_user=self.other, category="CONSULTATION", severity="INFO",
            title="Other", body="Other", data_json={},
        )
        response = self.client.get("/api/v1/notifications")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["unread_count"], 1)
        for _ in range(2):
            response = self.client.patch(f"/api/v1/notifications/{mine.id}/read")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data["is_read"])
        denied = self.client.patch(
            f"/api/v1/notifications/{Notification.objects.get(recipient_user=self.other).id}/read"
        )
        self.assertEqual(denied.status_code, 404)

    def test_preferences_keep_critical_enabled(self):
        response = self.client.patch(
            "/api/v1/notification-preferences",
            {"dnd_enabled": True, "dnd_start": "22:00", "dnd_end": "07:00",
             "categories": {"CRITICAL": False, "CONSULTATION": False}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        values = {item["category"]: item for item in response.data["categories"]}
        self.assertTrue(values["CRITICAL"]["enabled"])
        self.assertFalse(values["CONSULTATION"]["enabled"])
        self.assertIn("MEDICATION", values)

    def test_user_cannot_deactivate_another_users_token(self):
        token = FCMDeviceToken.objects.create(
            user=self.other, device="other-device", platform="ANDROID", token="other-token"
        )
        response = self.client.delete(f"/api/v1/devices/fcm-tokens/{token.id}")
        self.assertEqual(response.status_code, 404)
        token.refresh_from_db()
        self.assertTrue(token.is_active)

    def test_registering_same_installation_reassigns_it_to_current_user(self):
        token = FCMDeviceToken.objects.create(
            user=self.other, device="shared-installation", platform="ANDROID", token="old-token"
        )
        response = self.client.post(
            "/api/v1/devices/fcm-tokens",
            {"device_id": "shared-installation", "platform": "ANDROID", "token": "new-token"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.token, "new-token")
        self.assertTrue(token.is_active)


class FCMDeliveryTests(TestCase):
    def setUp(self):
        role = Role.objects.get(code="NEUROLOGIST")
        self.user = User.objects.create_user(
            "notification-fcm-user", "password", name="FCM user", role=role
        )
        self.notification = Notification.objects.create(
            recipient_user=self.user, category="CONSULTATION", severity="INFO",
            title="Sensitive source title", body="Sensitive source body",
            data_json={"event_type": "CONSULTATION_REQUESTED"},
        )

    @patch("apps.notifications.tasks.fcm.send_notification_device_fcm.delay")
    def test_fanout_queues_each_active_device_once(self, delay):
        active = [
            FCMDeviceToken.objects.create(
                user=self.user, device=f"device-{index}", platform="ANDROID",
                token=f"token-{index}", is_active=True,
            )
            for index in range(2)
        ]
        FCMDeviceToken.objects.create(
            user=self.user, device="inactive", platform="ANDROID",
            token="inactive-token", is_active=False,
        )

        result = send_notification_fcm.run(str(self.notification.id))

        self.assertEqual(result, {"queued": 2})
        self.assertEqual(delay.call_count, 2)
        self.assertEqual(
            {call.args[1] for call in delay.call_args_list},
            {str(device.id) for device in active},
        )

    @patch("apps.notifications.tasks.fcm.send_fcm_message")
    def test_permanent_invalid_token_is_deactivated(self, send):
        device = FCMDeviceToken.objects.create(
            user=self.user, device="invalid-device", platform="ANDROID", token="invalid-token"
        )
        send.side_effect = messaging.UnregisteredError("unregistered")

        result = send_notification_device_fcm.run(
            str(self.notification.id), str(device.id)
        )

        device.refresh_from_db()
        self.assertFalse(device.is_active)
        self.assertEqual(result, {"sent": 0, "deactivated": 1})

    def test_medication_reminder_uses_the_stored_push_text(self):
        notification = Notification.objects.create(
            recipient_user=self.user,
            category="MEDICATION",
            severity="INFO",
            title="복약 시간이에요",
            body="처방약 1정을 복용할 시간입니다.",
            data_json={"event_type": "MEDICATION_REMINDER"},
        )

        self.assertEqual(
            _safe_push_text(notification),
            (notification.title, notification.body),
        )

    def test_appointment_reminder_uses_the_stored_push_text(self):
        notification = Notification.objects.create(
            recipient_user=self.user,
            category="APPOINTMENT",
            severity="INFO",
            title="Appointment reminder",
            body="Your appointment is scheduled.",
            data_json={"event_type": "APPOINTMENT_REMINDER"},
        )

        self.assertEqual(
            _safe_push_text(notification),
            (notification.title, notification.body),
        )

    def test_finalized_prescription_uses_the_stored_push_text(self):
        notification = Notification.objects.create(
            recipient_user=self.user,
            category="PRESCRIPTION",
            severity="INFO",
            title="새 처방이 등록되었어요",
            body="새로운 처방이 등록되었습니다. 복약 일정을 확인해 주세요.",
            data_json={"event_type": "PRESCRIPTION_FINALIZED"},
        )

        self.assertEqual(
            _safe_push_text(notification),
            (notification.title, notification.body),
        )

    @patch("apps.notifications.tasks.fcm.send_fcm_message")
    def test_finalized_prescription_sends_the_stored_push_text(self, send):
        notification = Notification.objects.create(
            recipient_user=self.user,
            category="PRESCRIPTION",
            severity="INFO",
            title="새 처방이 등록되었어요",
            body="새로운 처방이 등록되었습니다. 복약 일정을 확인해 주세요.",
            data_json={
                "event_type": "PRESCRIPTION_FINALIZED",
                "prescription_id": "prescription-id",
            },
        )
        device = FCMDeviceToken.objects.create(
            user=self.user,
            device="prescription-device",
            platform="ANDROID",
            token="prescription-token",
        )

        result = send_notification_device_fcm.run(
            str(notification.id), str(device.id)
        )

        self.assertEqual(result, {"sent": 1})
        self.assertEqual(send.call_args.kwargs["title"], notification.title)
        self.assertEqual(send.call_args.kwargs["body"], notification.body)
        self.assertEqual(
            send.call_args.kwargs["data"]["event_type"],
            "PRESCRIPTION_FINALIZED",
        )

    @patch("apps.notifications.tasks.fcm.send_fcm_message")
    def test_medication_reminder_sends_the_stored_push_text(self, send):
        notification = Notification.objects.create(
            recipient_user=self.user,
            category="MEDICATION",
            severity="INFO",
            title="복약 시간이에요",
            body="처방약 1정을 복용할 시간입니다.",
            data_json={
                "event_type": "MEDICATION_REMINDER",
                "medication_schedule_id": "schedule-id",
                "medication_schedules": [
                    {
                        "medication_schedule_id": "schedule-id",
                        "medication_name": "Test medication",
                    }
                ],
            },
        )
        device = FCMDeviceToken.objects.create(
            user=self.user,
            device="medication-device",
            platform="ANDROID",
            token="medication-token",
        )

        result = send_notification_device_fcm.run(
            str(notification.id), str(device.id)
        )

        self.assertEqual(result, {"sent": 1})
        self.assertEqual(send.call_args.kwargs["title"], notification.title)
        self.assertEqual(send.call_args.kwargs["body"], notification.body)
        self.assertEqual(
            send.call_args.kwargs["data"]["medication_schedule_id"],
            "schedule-id",
        )
        self.assertEqual(
            json.loads(send.call_args.kwargs["data"]["medication_schedules"]),
            notification.data_json["medication_schedules"],
        )
