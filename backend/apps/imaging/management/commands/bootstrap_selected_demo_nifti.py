"""Register the three selected non-PHI demo cases stored in GCS.

The command creates only the Study/Series/NIfTI database metadata.  NIfTI
objects remain in their existing GCS buckets; no medical image is copied.
"""

from __future__ import annotations

import hashlib

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.imaging.models import ImagingStudy, NiftiArtifact, SeriesReference
from apps.imaging.services.nifti import parse_allowed_gcs_uri
from apps.patients.models import Patient, PatientCareAssignment


SELECTED_CASES = (
    {
        "patient_no": "MRA0001",
        "accession": "DEMO-MRA0001",
        "study_uid": "1.2.826.0.1.3680043.10.999.910.1",
        "modality": "MR",
        "description": "Demo cerebral aneurysm MRA",
        "inputs": (
            ("MRA", "gs://brainon-cdss-datasets/Anue/SegResNet/SegResNet_TopAneu_MRA/images/topaneu_center2_mr_032_0000.nii.gz"),
        ),
    },
    {
        "patient_no": "CT0001",
        "accession": "DEMO-CT0001",
        "study_uid": "1.2.826.0.1.3680043.10.999.910.2",
        "modality": "CT",
        "description": "Demo hemorrhagic stroke CT",
        "inputs": (
            ("CT", "gs://brainon-cdss-datasets/hemorrhage/v1/model_ready/nnunet/nnUNet_raw/Dataset001_ICHBinary/imagesTr/BHSD_ID_1cbe2853_ID_37afefdc7c_0000.nii.gz"),
        ),
    },
    {
        "patient_no": "MRI0003",
        "accession": "DEMO-MRI0003",
        "study_uid": "1.2.826.0.1.3680043.10.999.910.3",
        "modality": "MR",
        "description": "Demo ischemic stroke MRI DWI ADC",
        "inputs": (
            ("DWI", "gs://brainon-cdss-datasets/ischemia/v1/SegResNet/val/images/sub-strokecase0241_dwi.nii.gz"),
            ("ADC", "gs://brainon-cdss-datasets/ischemia/v1/SegResNet/val/images/sub-strokecase0241_adc.nii.gz"),
        ),
    },
)


class Command(BaseCommand):
    help = "Connect MRA0001, CT0001, and MRI0003 to the selected existing GCS NIfTI inputs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Verify patient and GCS object availability without writing database rows.",
        )
        parser.add_argument(
            "--clinician-login-id",
            help="Optionally grant the named clinician PRIMARY access to the three selected patients.",
        )

    def handle(self, *args, **options):
        from google.cloud import storage

        client = storage.Client()
        resolved_cases = [self._resolve_case(case, client) for case in SELECTED_CASES]
        clinician = self._resolve_clinician(options["clinician_login_id"])
        if options["check_only"]:
            self.stdout.write(self.style.SUCCESS("SELECTED_DEMO_NIFTI_PREFLIGHT: PASS"))
            return

        now = timezone.now()
        with transaction.atomic():
            for case in resolved_cases:
                study, _ = ImagingStudy.objects.update_or_create(
                    accession_number=case["accession"],
                    defaults={
                        "patient": case["patient"],
                        "imaging_order": None,
                        "study_instance_uid": case["study_uid"],
                        "orthanc_study": None,
                        "study_datetime": now,
                        "modalities": [case["modality"]],
                        "study_description": case["description"],
                        "series_count": len(case["inputs"]),
                        "instance_count": len(case["inputs"]),
                        "status": "AVAILABLE",
                        "last_synced_at": now,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                for series_number, item in enumerate(case["inputs"], start=1):
                    series, _ = SeriesReference.objects.update_or_create(
                        series_instance_uid=f"{case['study_uid']}.{series_number}",
                        defaults={
                            "study": study,
                            "orthanc_series": None,
                            "series_number": series_number,
                            "modality": case["modality"],
                            "series_description": item["role"],
                            "protocol_name": item["role"],
                            "instance_count": 1,
                            "frame_count": 0,
                            "rows": None,
                            "columns": None,
                            "slice_thickness": None,
                            "is_complete": True,
                            "is_ai_eligible": True,
                            "ai_exclusion_reason": "",
                            "created_at": now,
                            "updated_at": now,
                        },
                    )
                    conflicting = NiftiArtifact.objects.filter(uri=item["uri"]).exclude(series=series)
                    if conflicting.exists():
                        raise CommandError(
                            f"GCS URI already belongs to another series: {item['uri']}"
                        )
                    NiftiArtifact.objects.update_or_create(
                        series=series,
                        defaults={
                            "role": item["role"],
                            "uri": item["uri"],
                            "size_bytes": item["size_bytes"],
                            "sha256": item["sha256"],
                            "source": "PROTOTYPE_GCS",
                        },
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"CONNECTED patient={case['patient_no']} accession={case['accession']}"
                    )
                )
                if clinician is not None:
                    _, created = PatientCareAssignment.objects.get_or_create(
                        patient=case["patient"],
                        clinician=clinician,
                        role=PatientCareAssignment.AssignmentRole.PRIMARY,
                        status=PatientCareAssignment.Status.ACTIVE,
                        defaults={"source": PatientCareAssignment.Source.MANUAL},
                    )
                    assignment_state = "CREATED" if created else "EXISTING"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"ASSIGNMENT {assignment_state} "
                            f"clinician={clinician.login_id} patient={case['patient_no']}"
                        )
                    )

    def _resolve_case(self, case, client):
        patient = Patient.objects.filter(patient_no=case["patient_no"]).first()
        if patient is None:
            raise CommandError(f"Patient does not exist: {case['patient_no']}")
        inputs = []
        for role, uri in case["inputs"]:
            bucket_name, blob_name = parse_allowed_gcs_uri(uri)
            blob = client.bucket(bucket_name).blob(blob_name)
            if not blob.exists(client):
                raise CommandError(f"GCS object does not exist: {uri}")
            blob.reload()
            digest = hashlib.sha256()
            with blob.open("rb") as source:
                for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            inputs.append(
                {
                    "role": role,
                    "uri": uri,
                    "size_bytes": blob.size,
                    "sha256": digest.hexdigest(),
                }
            )
        return {**case, "patient": patient, "inputs": inputs}

    @staticmethod
    def _resolve_clinician(login_id):
        if not login_id:
            return None
        clinician = User.objects.filter(login_id__iexact=login_id, is_active=True).first()
        if clinician is None:
            raise CommandError(f"Active clinician does not exist: {login_id}")
        return clinician
