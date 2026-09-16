from django.test import SimpleTestCase

from config.celery_queues import (
    DEFAULT_QUEUE,
    INFERENCE_QUEUE,
    INTEGRATIONS_QUEUE,
    NOTIFICATIONS_QUEUE,
)
from config.celery import app


class CeleryQueueRoutingTests(SimpleTestCase):
    def route(self, task_name):
        return app.amqp.router.route({}, task_name, args=(), kwargs={})

    def test_domain_tasks_use_isolated_queues(self):
        cases = {
            "apps.ai_analysis.run_analysis_inference": INFERENCE_QUEUE,
            "apps.ai_analysis.tasks.future_task": INFERENCE_QUEUE,
            "apps.notifications.tasks.send_notification": NOTIFICATIONS_QUEUE,
            "apps.common.outbox_tasks.publish_outbox_event": INTEGRATIONS_QUEUE,
            "medication_safety.sync_mfds_dur_data": INTEGRATIONS_QUEUE,
            "common.broker_ping": DEFAULT_QUEUE,
            "apps.appointments.tasks.future_task": DEFAULT_QUEUE,
        }

        for task_name, expected_queue in cases.items():
            with self.subTest(task_name=task_name):
                self.assertEqual(self.route(task_name)["queue"].name, expected_queue)

    def test_workers_never_create_undeclared_queues(self):
        self.assertFalse(app.conf.task_create_missing_queues)
