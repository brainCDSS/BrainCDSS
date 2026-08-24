"""Health endpoint smoke test."""
from django.test import TestCase
class HealthTest(TestCase):
    def test_health(self):
        response=self.client.get("/api/v1/health/"); self.assertEqual(response.status_code,200); self.assertEqual(response.json()["status"],"ok"); self.assertIn("X-Trace-ID",response)

