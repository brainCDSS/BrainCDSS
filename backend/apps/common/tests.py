"""Health endpoint smoke test."""
from django.test import TestCase
from django.test import SimpleTestCase

class HealthTest(TestCase):
    def test_health(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("X-Trace-ID", response)


class CeleryTaskRegistrationTest(SimpleTestCase):
    def test_common_tasks_are_registered(self):
        from config.celery import app

        app.autodiscover_tasks(force=True)

        expected = {
            "common.broker_ping",
            "apps.common.outbox_tasks.publish_outbox_event",
            "apps.common.outbox_tasks.publish_pending_outbox_events",
        }

        missing = expected - set(app.tasks)

        self.assertFalse(
            missing,
            f"등록되지 않은 Celery task: {sorted(missing)}",
        )