"""Incremental refresh with an expiring DB lease and atomic per-disease publication."""
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..config import DISEASE_QUERIES
from ..models import ClinicalEvidence, DiseaseEvidence, EvidenceUpdateState
from .http import ExternalServiceError
from .pubmed import PubMedClient
from .ranking import rank_articles
from .summarizer import SUMMARY_FIELDS, VertexSummarizer, input_hash

logger = logging.getLogger(__name__)


def needs_summary(evidence, article, summarizer):
    return bool(article["abstract"].strip()) and (
        evidence.summary_status != "READY"
        or evidence.summary_model != summarizer.model
        or evidence.summary_version != summarizer.version
        or evidence.summary_input_hash != input_hash(article)
    )


def upsert_article(article, disease, summarizer, *, generate_summaries=True):
    defaults = {key: value for key, value in article.items() if key != "pmid"}
    defaults["fetched_at"] = timezone.now()
    # Canonical disease_type records first discovery. Membership handles overlaps.
    evidence, created = ClinicalEvidence.objects.get_or_create(
        pmid=article["pmid"], defaults={"disease_type": disease, **defaults},
    )
    for key, value in defaults.items():
        setattr(evidence, key, value)
    if not article["abstract"].strip():
        for field in SUMMARY_FIELDS.values():
            setattr(evidence, field, None)
        evidence.summary_status = "NO_ABSTRACT"
        evidence.summary_source = ""
        evidence.summary_model = ""
        evidence.summary_generated_at = None
        evidence.summary_version = ""
        evidence.summary_input_hash = ""
    elif needs_summary(evidence, article, summarizer):
        # Never display a stale summary for changed input/model/version.
        for field in SUMMARY_FIELDS.values():
            setattr(evidence, field, None)
        evidence.summary_generated_at = None
        evidence.summary_source = ""
        evidence.summary_status = "PENDING"
        if generate_summaries:
            try:
                summary = summarizer.summarize(article)
                if not summary:
                    raise ExternalServiceError("SUMMARY_EMPTY")
                for key, value in summary.items():
                    setattr(evidence, key, value)
                evidence.summary_source = "PUBMED_ABSTRACT"
                evidence.summary_model = summarizer.model
                evidence.summary_version = summarizer.version
                evidence.summary_input_hash = input_hash(article)
                evidence.summary_generated_at = timezone.now()
                evidence.summary_status = "READY"
            except Exception:
                # No raw exception: SDK/network errors can contain credentials.
                evidence.summary_status = "ERROR"
                logger.warning("clinical_evidence summary failed pmid=%s code=SUMMARY_FAILED", evidence.pmid)
    evidence.save()
    return evidence, created


def _acquire_lease(owner):
    now = timezone.now()
    EvidenceUpdateState.objects.get_or_create(key="job")
    return EvidenceUpdateState.objects.filter(key="job").filter(
        Q(lease_until__isnull=True) | Q(lease_until__lte=now)
    ).update(lease_owner=owner, lease_until=now + timedelta(hours=2), last_attempt_at=now) == 1


def _publish(disease, articles, owner):
    with transaction.atomic():
        lease = EvidenceUpdateState.objects.select_for_update().get(key="job")
        if lease.lease_owner != owner or lease.lease_until <= timezone.now():
            raise ExternalServiceError("UPDATE_LEASE_EXPIRED")
        DiseaseEvidence.objects.filter(disease_type=disease).update(is_active=False)
        for rank, evidence in enumerate(articles, 1):
            DiseaseEvidence.objects.update_or_create(evidence=evidence, disease_type=disease,
                defaults={"display_rank": rank, "is_active": True})
        # Article-level fields are canonical; API uses disease-specific rank.
        for evidence in ClinicalEvidence.objects.filter(selections__disease_type=disease).distinct():
            active = evidence.selections.filter(is_active=True)
            evidence.is_active = active.exists()
            evidence.display_rank = min(active.values_list("display_rank", flat=True), default=0)
            evidence.save(update_fields=["is_active", "display_rank", "updated_at"])
        EvidenceUpdateState.objects.filter(key=disease).update(
            last_success_at=timezone.now(), last_error_code="")


def update_clinical_evidence(*, diseases=None, client=None, summarizer=None, generate_summaries=True):
    diseases = tuple(diseases or DISEASE_QUERIES)
    if any(disease not in DISEASE_QUERIES for disease in diseases):
        raise ValueError("Unknown disease")
    if not 1 <= settings.CLINICAL_EVIDENCE_SEARCH_LIMIT <= 200 or not 1 <= settings.CLINICAL_EVIDENCE_STORE_LIMIT <= 30:
        raise ValueError("Clinical evidence limits out of bounds")
    owner = str(uuid.uuid4())
    if not _acquire_lease(owner):
        return {"status": "ALREADY_RUNNING", "diseases": {}}
    client = client or PubMedClient()
    summarizer = summarizer or VertexSummarizer()
    report = {"status": "SUCCESS", "diseases": {}}
    try:
        for disease in diseases:
            EvidenceUpdateState.objects.update_or_create(key=disease, defaults={"last_attempt_at": timezone.now()})
            try:
                pmids = client.search(disease)
                metadata = client.fetch(pmids)
                if {item["pmid"] for item in metadata} != set(pmids):
                    raise ExternalServiceError("PUBMED_INCOMPLETE_BATCH")
                candidates = rank_articles(metadata, disease)[:settings.CLINICAL_EVIDENCE_STORE_LIMIT]
                saved, inserted, failures = [], 0, 0
                for article in candidates:
                    try:
                        evidence, created = upsert_article(article, disease, summarizer,
                            generate_summaries=generate_summaries)
                        saved.append(evidence)
                        inserted += int(created)
                    except Exception:
                        failures += 1
                        logger.warning("clinical_evidence article failed pmid=%s code=ARTICLE_SAVE_FAILED", article["pmid"])
                if failures:
                    raise ExternalServiceError("ARTICLE_SAVE_FAILED")
                _publish(disease, saved, owner)
                report["diseases"][disease] = {"selected": len(saved), "inserted": inserted,
                    "summary_ready": sum(item.summary_status == "READY" for item in saved)}
            except Exception:
                logger.warning("clinical_evidence update failed disease=%s code=UPDATE_FAILED", disease)
                EvidenceUpdateState.objects.filter(key=disease).update(last_error_code="UPDATE_FAILED")
                report["status"] = "PARTIAL_FAILURE"
                report["diseases"][disease] = {"error": "UPDATE_FAILED"}
    finally:
        EvidenceUpdateState.objects.filter(key="job", lease_owner=owner).update(lease_until=None, lease_owner="")
    return report
