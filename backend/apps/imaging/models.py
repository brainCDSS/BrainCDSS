"""Imaging persistence models and NIfTI artifacts derived from DICOM."""

import uuid

from django.db import models

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import ImagingOrder, ImagingStudy, SeriesReference, DicomObjectReference, ImagingOrderStatusHistory, DicomTransferJob, ImagingReconciliationTask, KeyImageSelection
# === FINAL_DB_GENERATED_IMPORTS_END ===


class NiftiArtifact(models.Model):
    """Immutable GCS object associated with an imaging series."""

    ROLE_CHOICES = (("CT", "CT"), ("DWI", "DWI"), ("ADC", "ADC"), ("MRA", "MRA"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.OneToOneField(
        SeriesReference, on_delete=models.CASCADE, related_name="nifti_artifact"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, db_index=True)
    uri = models.CharField(max_length=1024, unique=True)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    source = models.CharField(max_length=24, default="DICOM_CONVERSION")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "imaging_niftiartifact"
