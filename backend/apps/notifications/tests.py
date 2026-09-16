from django.test import TestCase

from apps.accounts.models import Role, User
from apps.notifications.models import NotificationCategoryPreference
from apps.notifications.services.notifications import create_notification_for_user


class NotificationCreationPreferenceTests(TestCase):
    def setUp(self):
        role = Role.objects.create(code="NEUROLOGIST", name="Neurologist")
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
