"""NCBI ESearch/EFetch; metadata parsing is independent from network I/O."""
import calendar
import json
import logging
import re
import time
from datetime import date
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from django.conf import settings

from ..config import build_query
from .http import ExternalServiceError, request_bytes

logger = logging.getLogger(__name__)
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def valid_pmid(value):
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,15}", value) is not None


def parse_pmids(body):
    try:
        payload = json.loads(body)
        result = payload["esearchresult"]
        if payload.get("error") or result.get("errorlist"):
            raise ValueError("PubMed rejected query")
        ids = result["idlist"]
        if not isinstance(ids, list) or any(not valid_pmid(pmid) for pmid in ids):
            raise ValueError("Invalid PMID")
        return list(dict.fromkeys(ids))
    except (ValueError, KeyError, TypeError):
        raise ExternalServiceError("PUBMED_INVALID_SEARCH_RESPONSE") from None


def _text(element):
    return "" if element is None else "".join(element.itertext()).strip()


def _publication_date(article):
    """Do not invent day/month precision for year-only or seasonal dates."""
    nodes = article.findall(".//ArticleDate[@DateType='Electronic']")
    nodes += article.findall("./Journal/JournalIssue/PubDate")
    year = None
    for node in nodes:
        year_text = node.findtext("Year") or node.findtext("MedlineDate") or ""
        match = re.search(r"\b(\d{4})\b", year_text)
        if not match:
            continue
        y = int(match.group(1))
        if not 1800 <= y <= 2200:
            continue
        year = year or y
        month = node.findtext("Month", "")
        day = node.findtext("Day", "")
        if not month.isdigit():
            month = str({name.lower(): i for i, name in enumerate(calendar.month_abbr) if i}.get(month.lower(), ""))
        try:
            return date(y, int(month), int(day)), y
        except (ValueError, TypeError):
            continue
    return None, year


def parse_metadata(body):
    # PubMed includes a standard external DTD. ElementTree does not fetch it.
    # Reject entity declarations/internal subsets before parsing untrusted XML.
    if re.search(br"<!ENTITY|<!DOCTYPE[^>]*\[", body, re.I):
        raise ExternalServiceError("PUBMED_UNSAFE_XML")
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise ExternalServiceError("PUBMED_INVALID_XML") from None
    if root.tag != "PubmedArticleSet" or root.findall(".//ERROR"):
        raise ExternalServiceError("PUBMED_INVALID_FETCH_RESPONSE")
    parsed = []
    for entry in root.findall("PubmedArticle"):
        article = entry.find("./MedlineCitation/Article")
        pmid = entry.findtext("./MedlineCitation/PMID", "").strip()
        if article is None or not valid_pmid(pmid) or not _text(article.find("ArticleTitle")):
            logger.warning("clinical_evidence metadata skipped: INVALID_ARTICLE")
            continue
        publication_date, year = _publication_date(article)
        authors = []
        for author in article.findall("./AuthorList/Author"):
            authors.append(_text(author.find("CollectiveName")) or " ".join(filter(None, [author.findtext("ForeName"), author.findtext("LastName")])))
        abstract = []
        for part in article.findall("./Abstract/AbstractText"):
            abstract.append((part.get("Label", "") + ": " if part.get("Label") else "") + _text(part))
        identifiers = {node.get("IdType"): _text(node) for node in entry.findall("./PubmedData/ArticleIdList/ArticleId")}
        doi = identifiers.get("doi") or article.findtext("./ELocationID[@EIdType='doi']")
        pmcid = identifiers.get("pmc")
        parsed.append({
            "pmid": pmid, "title": _text(article.find("ArticleTitle")),
            "journal": _text(article.find("Journal/Title"))[:512],
            "authors": [name for name in authors if name],
            "publication_date": publication_date, "publication_year": year,
            "publication_type": [_text(node) for node in article.findall("./PublicationTypeList/PublicationType")],
            "abstract": "\n".join(abstract), "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi": doi[:256] if doi and re.fullmatch(r"10\.\d{4,9}/\S+", doi) else None,
            "pmcid": pmcid if pmcid and re.fullmatch(r"PMC[1-9][0-9]{0,20}", pmcid) else None,
        })
    return parsed


class PubMedClient:
    def __init__(self):
        self._last_request = 0.0

    def _request(self, endpoint, params):
        gap = 0.12 if settings.CLINICAL_EVIDENCE_PUBMED_API_KEY else 0.36
        time.sleep(max(0, gap - (time.monotonic() - self._last_request)))
        params = {"db": "pubmed", "tool": "brainon_clinical_evidence", **params}
        if settings.CLINICAL_EVIDENCE_PUBMED_EMAIL:
            params["email"] = settings.CLINICAL_EVIDENCE_PUBMED_EMAIL
        if settings.CLINICAL_EVIDENCE_PUBMED_API_KEY:
            params["api_key"] = settings.CLINICAL_EVIDENCE_PUBMED_API_KEY
        try:
            # POST prevents long query strings and API keys appearing in URLs/logs.
            return request_bytes(BASE_URL + endpoint, data=urlencode(params).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                                 timeout=settings.CLINICAL_EVIDENCE_HTTP_TIMEOUT)
        finally:
            self._last_request = time.monotonic()

    def search(self, disease):
        return parse_pmids(self._request("esearch.fcgi", {
            "term": build_query(disease), "retmode": "json", "sort": "pub_date",
            "retmax": settings.CLINICAL_EVIDENCE_SEARCH_LIMIT,
        }))

    def fetch(self, pmids):
        if not pmids:
            return []
        if any(not valid_pmid(pmid) for pmid in pmids):
            raise ValueError("Invalid PMID")
        return parse_metadata(self._request("efetch.fcgi", {"id": ",".join(pmids), "retmode": "xml"}))
