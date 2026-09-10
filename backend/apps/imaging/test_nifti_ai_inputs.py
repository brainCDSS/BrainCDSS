from django.test import TestCase
from django.utils import timezone

from apps.imaging.models import ImagingStudy, NiftiArtifact, SeriesReference
from apps.imaging.services.nifti import study_input_bundles


class NiftiAIInputTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.study = ImagingStudy.objects.create(
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
