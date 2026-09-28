"""Central, field-aware PubMed search and editorial ranking configuration."""
import re
from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings


@dataclass(frozen=True)
class DiseaseQuery:
    conditions: tuple[str, ...]
    clinical_topics: tuple[str, ...]


DISEASE_QUERIES = {
    "ischemic_stroke": DiseaseQuery(
        ("acute ischemic stroke", "ischemic stroke", "cerebral infarction"),
        ("diagnosis", "treatment", "thrombolysis", "thrombectomy", "antiplatelet",
         "prognosis", "secondary prevention", "guideline"),
    ),
    "intracranial_hemorrhage": DiseaseQuery(
        ("intracerebral hemorrhage", "intracranial hemorrhage"),
        ("diagnosis", "blood pressure management", "anticoagulation reversal",
         "surgery", "hematoma expansion", "prognosis", "guideline"),
    ),
    "intracranial_aneurysm": DiseaseQuery(
        ("intracranial aneurysm", "cerebral aneurysm"),
        ("rupture risk", "treatment", "clipping", "coiling", "flow diversion",
         "surveillance", "prognosis", "guideline"),
    ),
}
DISEASE_CHOICES = tuple((name, name) for name in DISEASE_QUERIES)
PUBLICATION_PRIORITY = {
    "Practice Guideline": 0, "Guideline": 0, "Meta-Analysis": 1,
    "Systematic Review": 2, "Randomized Controlled Trial": 3,
    "Clinical Trial": 4, "Clinical Trial, Phase III": 4,
    "Clinical Trial, Phase IV": 4, "Controlled Clinical Trial": 4,
    "Observational Study": 4, "Comparative Study": 4, "Multicenter Study": 4,
    "Review": 5,
}
EXCLUDED_TYPES = frozenset({"Case Reports", "Editorial", "Comment", "Letter",
                            "Retracted Publication", "Retraction of Publication"})
EXCLUDED_TITLE_TERMS = ("artificial intelligence", "deep learning", "machine learning",
                        "segmentation", "neural network", "radiomics")


def _group(terms, field):
    if field not in {"Title/Abstract", "Title", "Publication Type"}:
        raise ValueError("Unsupported PubMed field")
    quoted = []
    for term in terms:
        if not re.fullmatch(r"[A-Za-z0-9 ,\-]+", term):
            raise ValueError("Unsafe PubMed term")
        quoted.append(f'"{term}"[{field}]')
    return "(" + " OR ".join(quoted) + ")"


def build_query(disease, *, today=None, lookback_days=None):
    """Only trusted server config enters syntax; request input selects a known key."""
    config = DISEASE_QUERIES[disease]
    today = today or date.today()
    days = lookback_days if lookback_days is not None else settings.CLINICAL_EVIDENCE_LOOKBACK_DAYS
    if not 1 <= days <= 3650:
        raise ValueError("lookback_days must be between 1 and 3650")
    start = today - timedelta(days=days)
    positive = " AND ".join([
        _group(config.conditions, "Title/Abstract"),
        _group(config.clinical_topics, "Title/Abstract"),
        _group(PUBLICATION_PRIORITY, "Publication Type"),
        f'("{start:%Y/%m/%d}"[Date - Publication] : "{today:%Y/%m/%d}"[Date - Publication])',
    ])
    # PubMed uses binary NOT. `AND NOT (...)` is parsed as a missing operand and
    # can silently drop the negation, so exclusions must follow the positive set.
    return (positive
            + ' NOT ("animals"[MeSH Terms] NOT "humans"[MeSH Terms])'
            + " NOT " + _group(EXCLUDED_TITLE_TERMS, "Title")
            + " NOT " + _group(sorted(EXCLUDED_TYPES), "Publication Type"))
