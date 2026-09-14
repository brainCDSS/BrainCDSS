import hashlib

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.imaging.models import ImagingStudy, NiftiArtifact, SeriesReference
from apps.imaging.services.nifti import parse_allowed_gcs_uri
from apps.patients.models import Patient


DEMO_CASES = (
    {
        "uid_suffix": 1, "patient_no": "FT-I001", "accession": "DEMO-ISCH-001", "modalities": ["MR"],
        "description": "Demo brain MRI DWI ADC", "inputs": (
            ("DWI", "gs://brainon-cdss-datasets/ischemia/v1/SegResNet/test/images/sub-strokecase0189_dwi.nii.gz"),
            ("ADC", "gs://brainon-cdss-datasets/ischemia/v1/SegResNet/test/images/sub-strokecase0189_adc.nii.gz"),
        ),
    },
    {
        "uid_suffix": 2, "patient_no": "FT-H001", "accession": "DEMO-HEM-001", "modalities": ["CT"],
        "description": "Demo non-contrast brain CT", "inputs": (
            ("CT", "gs://brainon-cdss-datasets/hemorrhage/v1/model_ready/nnunet/nnUNet_raw/Dataset001_ICHBinary/imagesTr/BHSD_ID_07365cde_ID_8e661b8f07_0000.nii.gz"),
        ),
    },
    {
        "uid_suffix": 3, "patient_no": "FT-A001", "accession": "DEMO-ANE-001", "modalities": ["MR"],
        "description": "Demo brain MRA", "inputs": (
            ("MRA", "gs://brainon-cdss-datasets/Anue/SegResNet/SegResNet_TopAneu_MRA/images/topaneu_center2_mr_032_0000.nii.gz"),
        ),
    },
    {
        "uid_suffix": 4, "patient_no": "FT-I002", "accession": "DEMO-ISCH-002", "modalities": ["MR"],
        "description": "Demo brain MRI DWI ADC", "inputs": (
            ("DWI", "gs://brainon-cdss-datasets/ischemia/v1/SegResNet/test/images/sub-strokecase0063_dwi.nii.gz"),
            ("ADC", "gs://brainon-cdss-datasets/ischemia/v1/SegResNet/test/images/sub-strokecase0063_adc.nii.gz"),
        ),
    },
    {
        "uid_suffix": 5, "patient_no": "FT-H002", "accession": "DEMO-HEM-002", "modalities": ["CT"],
        "description": "Demo non-contrast brain CT", "inputs": (
            ("CT", "gs://brainon-cdss-datasets/hemorrhage/v1/model_ready/nnunet/nnUNet_raw/Dataset001_ICHBinary/imagesTr/BHSD_ID_981d95a4_ID_ec08553ddc_0000.nii.gz"),
        ),
    },
    {
        "uid_suffix": 6, "patient_no": "FT-A002", "accession": "DEMO-ANE-002", "modalities": ["MR"],
        "description": "Demo brain MRA", "inputs": (
            ("MRA", "gs://brainon-cdss-datasets/Anue/SegResNet/SegResNet_TopAneu_MRA/images/topaneu_center5_mr_081_0000.nii.gz"),
        ),
    },
)


class Command(BaseCommand):
    help = "Create six synthetic-patient studies and register their existing GCS NIfTI inputs."

    def handle(self, *args, **options):
        from google.cloud import storage

        client = storage.Client()
        now = timezone.now()
        for case in DEMO_CASES:
            patient = Patient.objects.filter(patient_no=case["patient_no"]).first()
            if patient is None:
                raise CommandError(f"Demo patient does not exist: {case['patient_no']}")
            study, _ = ImagingStudy.objects.update_or_create(
                accession_number=case["accession"],
                defaults={
                    "patient": patient, "imaging_order": None,
                    "study_instance_uid": f"1.2.826.0.1.3680043.10.999.900.{case['uid_suffix']}",
                    "orthanc_study": None, "study_datetime": now,
                    "modalities": case["modalities"], "study_description": case["description"],
                    "series_count": len(case["inputs"]), "instance_count": len(case["inputs"]),
                    "status": "AVAILABLE", "last_synced_at": now,
                    "created_at": now, "updated_at": now,
                },
            )
            for series_number, (role, uri) in enumerate(case["inputs"], start=1):
                bucket_name, blob_name = parse_allowed_gcs_uri(uri)
                blob = client.bucket(bucket_name).blob(blob_name)
                blob.reload()
                digest = hashlib.sha256()
                with blob.open("rb") as source:
                    for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                series, _ = SeriesReference.objects.update_or_create(
                    series_instance_uid=f"{study.study_instance_uid}.{series_number}",
                    defaults={
                        "study": study, "orthanc_series": None, "series_number": series_number,
                        "modality": case["modalities"][0], "series_description": role,
                        "protocol_name": role, "instance_count": 1, "frame_count": 0,
                        "rows": None, "columns": None, "slice_thickness": None,
                        "is_complete": True, "is_ai_eligible": True,
                        "ai_exclusion_reason": "", "created_at": now, "updated_at": now,
                    },
                )
                NiftiArtifact.objects.update_or_create(
                    series=series,
                    defaults={
                        "role": role, "uri": uri, "size_bytes": blob.size,
                        "sha256": digest.hexdigest(), "source": "PROTOTYPE_GCS",
                    },
                )
            self.stdout.write(self.style.SUCCESS(f"Connected {case['patient_no']} to {case['accession']}"))
