from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from unittest.mock import patch

from apps.accounts.models import Role, User
from apps.imaging.api.nifti import (
    ImagingStudyCollectionView,
    NiftiArtifactContentView,
    StudyNiftiViewerView,
)
from apps.imaging.models import ImagingStudy, NiftiArtifact, SeriesReference
from apps.imaging.services.nifti import study_input_bundles
from apps.patients.models import Patient, PatientCareAssignment


class NiftiAIInputTests(TestCase):
    def setUp(self):
        now = timezone.now()
        role = Role.objects.get(code="RADIOLOGY")
        self.user = User.objects.create_user(
            login_id="synthetic-imaging-user", password="test-only-password",
            name="Synthetic Imaging User", role=role,
        )
        self.patient = Patient.objects.create(
            patient_no="SYNTHETIC-NIFTI-PATIENT",
            name="Synthetic Imaging Patient",
            created_by=self.user,
        )
        PatientCareAssignment.objects.create(
            patient=self.patient,
            clinician=self.user,
            role=PatientCareAssignment.AssignmentRole.PRIMARY,
            source=PatientCareAssignment.Source.MANUAL,
        )
        self.study = ImagingStudy.objects.create(
            patient=self.patient,
            study_instance_uid="1.2.826.0.1.3680043.10.999.200",
            accession_number="SYNTHETIC-NIFTI",
            study_datetime=now,
            modalities=["MR"],
            study_description="Synthetic DWI ADC pairing test",
            series_count=2,
            instance_count=64,
            status="AVAILABLE",
            last_synced_at=now,
            created_at=now,
            updated_at=now,
        )

    def add_artifact(self, role, number):
        now = timezone.now()
        series = SeriesReference.objects.create(
            study=self.study,
            series_instance_uid=f"1.2.826.0.1.3680043.10.999.200.{number}",
            series_number=number,
            modality="MR",
            series_description=role,
            protocol_name=role,
            instance_count=32,
            frame_count=32,
            rows=256,
            columns=256,
            is_complete=True,
            is_ai_eligible=True,
            ai_exclusion_reason="",
            created_at=now,
            updated_at=now,
        )
        return NiftiArtifact.objects.create(
            series=series,
            role=role,
            uri=f"gs://brainon-cdss-datasets/synthetic/{role.lower()}.nii.gz",
            size_bytes=100,
            sha256=str(number) * 64,
            source="PROTOTYPE_GCS",
        )

    def test_ischemia_requires_both_dwi_and_adc(self):
        self.add_artifact("DWI", 1)
        ischemia = next(
            item for item in study_input_bundles(self.study)
            if item["analysis_type"] == "ISCHEMIC_STROKE_DWI_ADC"
        )
        self.assertFalse(ischemia["ready"])
        self.assertEqual(ischemia["missing_roles"], ["ADC"])

        self.add_artifact("ADC", 2)
        ischemia = next(
            item for item in study_input_bundles(self.study)
            if item["analysis_type"] == "ISCHEMIC_STROKE_DWI_ADC"
        )
        self.assertTrue(ischemia["ready"])
        self.assertEqual([item["role"] for item in ischemia["inputs"]], ["DWI", "ADC"])

    def test_study_collection_returns_one_study_instead_of_series_rows(self):
        self.add_artifact("DWI", 1)
        self.add_artifact("ADC", 2)
        request = APIRequestFactory().get("/api/v1/imaging-studies")
        force_authenticate(request, user=self.user)

        response = ImagingStudyCollectionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["study_id"], str(self.study.id))
        self.assertEqual(response.data["results"][0]["series_count"], 2)
        self.assertEqual(response.data["results"][0]["status"], "AVAILABLE")

    @patch("apps.imaging.api.nifti.create_signed_gcs_artifact_uri")
    def test_artifact_content_redirects_to_signed_gcs_url(self, signed_url):
        artifact = self.add_artifact("MRA", 1)
        signed_url.return_value = "https://storage.googleapis.com/signed-object"
        request = APIRequestFactory().get(
            f"/api/v1/nifti-artifacts/{artifact.id}/content"
        )
        force_authenticate(request, user=self.user)

        response = NiftiArtifactContentView.as_view()(request, artifact.id)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], signed_url.return_value)
        signed_url.assert_called_once_with(artifact)

    @patch("apps.imaging.api.nifti.create_signed_gcs_artifact_uri")
    def test_study_viewer_manifest_contains_only_source_images(self, signed_url):
        self.add_artifact("ADC", 2)
        self.add_artifact("DWI", 1)
        signed_url.side_effect = lambda artifact: f"https://example.test/{artifact.role}"
        request = APIRequestFactory().get(
            f"/api/v1/imaging-studies/{self.study.id}/nifti-viewer"
        )
        force_authenticate(request, user=self.user)

        response = StudyNiftiViewerView.as_view()(request, self.study.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["role"] for item in response.data["inputs"]], ["DWI", "ADC"])
        self.assertEqual(response.data["masks"], [])
