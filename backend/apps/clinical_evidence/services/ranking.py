"""Editorial publication-type priority, not an automated GRADE assessment."""
from datetime import date

from ..config import DISEASE_QUERIES, EXCLUDED_TITLE_TERMS, EXCLUDED_TYPES, PUBLICATION_PRIORITY


def evidence_priority(article):
    types = set(article["publication_type"])
    if types & EXCLUDED_TYPES or any(term in article["title"].lower() for term in EXCLUDED_TITLE_TERMS):
        return None
    return min((PUBLICATION_PRIORITY[t] for t in types if t in PUBLICATION_PRIORITY), default=None)


def rank_articles(articles, disease=None):
    eligible = [item for item in articles if evidence_priority(item) is not None]
    def key(item):
        published = item["publication_date"] or date(item["publication_year"] or 1800, 1, 1)
        title = item["title"].lower()
        title_relevance = int(bool(disease and any(term in title for term in DISEASE_QUERIES[disease].conditions)))
        return evidence_priority(item), -title_relevance, -published.toordinal(), -int(item["pmid"])
    return sorted(eligible, key=key)
