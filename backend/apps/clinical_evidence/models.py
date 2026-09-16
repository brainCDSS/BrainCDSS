from django.db import models

from .config import DISEASE_CHOICES


class ClinicalEvidence(models.Model):
    """One record per PMID; no patient data is stored or sent to the model."""
    pmid = models.CharField(max_length=16, unique=True)
    disease_type = models.CharField(max_length=40, choices=DISEASE_CHOICES)
    title = models.TextField()
    journal = models.CharField(max_length=512, blank=True)
    authors = models.JSONField(default=list)
    publication_date = models.DateField(null=True, blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    publication_type = models.JSONField(default=list)
    abstract = models.TextField(blank=True)
    summary_short = models.TextField(null=True, blank=True)
    summary_objective = models.TextField(null=True, blank=True)
    summary_methods = models.TextField(null=True, blank=True)
    summary_results = models.TextField(null=True, blank=True)
    summary_clinical_significance = models.TextField(null=True, blank=True)
    summary_limitations = models.TextField(null=True, blank=True)
    summary_source = models.CharField(max_length=64, blank=True)
    summary_model = models.CharField(max_length=128, blank=True)
    summary_generated_at = models.DateTimeField(null=True, blank=True)
    summary_status = models.CharField(max_length=24, default="PENDING")
    summary_version = models.CharField(max_length=40, blank=True)
    summary_input_hash = models.CharField(max_length=64, blank=True)
    pubmed_url = models.URLField(max_length=256)
    doi = models.CharField(max_length=256, null=True, blank=True)
    pmcid = models.CharField(max_length=24, null=True, blank=True)
    display_rank = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    fetched_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_evidence"


class DiseaseEvidence(models.Model):
    """Separate membership/rank allows one PMID to appear in several diseases."""
    evidence = models.ForeignKey(ClinicalEvidence, on_delete=models.CASCADE, related_name="selections")
    disease_type = models.CharField(max_length=40, choices=DISEASE_CHOICES)
    display_rank = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "clinical_evidence_selection"
        constraints = [models.UniqueConstraint(fields=["evidence", "disease_type"], name="unique_evidence_disease")]
        indexes = [models.Index(fields=["disease_type", "is_active", "display_rank"], name="evidence_disease_rank_idx")]


class EvidenceUpdateState(models.Model):
    """Last successful refresh per disease; 'job' row is an expiring DB lease."""
    key = models.CharField(max_length=40, primary_key=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=64, blank=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_owner = models.CharField(max_length=36, blank=True)

    class Meta:
        db_table = "clinical_evidence_update_state"
