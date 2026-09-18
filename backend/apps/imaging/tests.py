from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Role, User
from apps.imaging.api.patient_test_results_views import PatientTestResultsView
from apps.imaging.models import ImagingStudy
from apps.patients.models import Patient


class PatientTestResultsViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        role = Role.objects.create(code="PATIENT", name="Patient")
        self.user = User.objects.create_user(
            login_id="test-result-patient",
            password="test-password",
            name="Test Patient",
            role=role,
        )
        self.patient = Patient.objects.create(
            user=self.user,
            patient_no="TEST-RESULT-PATIENT",
            name="Test Patient",
            created_by=self.user,
        )
        self.other_user = User.objects.create_user(
            login_id="other-test-result-patient",
            password="test-password",
            name="Other Patient",
            role=role,
        )
        self.other_patient = Patient.objects.create(
            user=self.other_user,
            patient_no="OTHER-RESULT-PATIENT",
            name="Other Patient",
            created_by=self.other_user,
        )

    def create_study(self, patient, suffix, study_datetime):
        return ImagingStudy.objects.create(
            patient=patient,
            study_instance_uid=f"1.2.826.0.1.3680043.10.999.{suffix}",
            accession_number=f"ACC-{suffix}",
            study_datetime=study_datetime,
            modalities=["CT"],
            study_description=f"Study {suffix}",
            series_count=1,
            instance_count=1,
            status="AVAILABLE",
            last_synced_at=study_datetime,
            created_at=study_datetime,
            updated_at=study_datetime,
        )

    def test_returns_only_current_patients_studies_newest_first(self):
        now = timezone.now()
        older = self.create_study(self.patient, "100", now - timedelta(days=1))
        newer = self.create_study(self.patient, "101", now)
        self.create_study(self.other_patient, "102", now + timedelta(days=1))

        request = self.factory.get("/api/v1/me/test-results")
        force_authenticate(request, user=self.user)
        response = PatientTestResultsView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["study_id"] for row in response.data["results"]],
            [newer.id, older.id],
        )
        self.assertEqual(
            set(response.data["results"][0]),
            {"study_id", "study_datetime", "modalities", "study_description"},
        )
