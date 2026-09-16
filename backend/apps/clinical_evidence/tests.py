import json
from datetime import date
from types import SimpleNamespace

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from .api.views import ClinicalEvidenceView
from .config import DISEASE_QUERIES, build_query
from .models import ClinicalEvidence, DiseaseEvidence, EvidenceUpdateState
from .services.http import ExternalServiceError
from .services.pubmed import parse_metadata, parse_pmids
from .services.ranking import rank_articles
from .services.summarizer import parse_summary
from .services.update import update_clinical_evidence, upsert_article


ARTICLE = {
    "pmid": "12345678", "title": "Treatment of acute ischemic stroke", "journal": "Stroke",
    "authors": ["Kim A"], "publication_date": date(2026, 9, 1), "publication_year": 2026,
    "publication_type": ["Randomized Controlled Trial"], "abstract": "A randomized trial reported outcomes.",
    "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/", "doi": None, "pmcid": None,
}


class PubMedTests(TestCase):
    def test_queries_are_fielded_and_disease_specific(self):
        for disease in DISEASE_QUERIES:
            query = build_query(disease, today=date(2026, 9, 16), lookback_days=365)
            self.assertIn("[Title/Abstract]", query)
            self.assertIn("[Publication Type]", query)
            self.assertIn("[Date - Publication]", query)
            self.assertIn("NOT", query)

    def test_pmid_and_metadata_parsing_with_missing_optional_fields(self):
        self.assertEqual(parse_pmids(json.dumps({"esearchresult": {"idlist": ["123", "456"]}})), ["123", "456"])
        xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
        <Journal><JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue><Title>Stroke</Title></Journal>
        <ArticleTitle>Clinical treatment study</ArticleTitle><PublicationTypeList><PublicationType>Review</PublicationType></PublicationTypeList>
        </Article></MedlineCitation><PubmedData><ArticleIdList /></PubmedData></PubmedArticle></PubmedArticleSet>"""
        result = parse_metadata(xml)[0]
        self.assertEqual(result["abstract"], "")
        self.assertIsNone(result["doi"])
        self.assertIsNone(result["pmcid"])
        self.assertIsNone(result["publication_date"])
        self.assertEqual(result["publication_year"], 2026)

    def test_rejects_bad_pmids_and_unsafe_xml(self):
        with self.assertRaises(ExternalServiceError):
            parse_pmids(json.dumps({"esearchresult": {"idlist": ["not-an-id"]}}))
        with self.assertRaises(ExternalServiceError):
            parse_metadata(b'<!DOCTYPE x [<!ENTITY y "z">]><PubmedArticleSet/>')


class SummaryAndRankingTests(TestCase):
    def test_structured_summary_and_invalid_payload(self):
        payload = {key: "value" for key in ("short_summary", "objective", "population_and_methods", "key_results", "clinical_significance", "limitations")}
        self.assertEqual(parse_summary(json.dumps(payload))["summary_short"], "value")
        with self.assertRaises(ExternalServiceError):
            parse_summary("not json")

    def test_evidence_priority_then_recency_and_exclusions(self):
        guideline = {**ARTICLE, "pmid": "1", "publication_type": ["Guideline"], "publication_date": date(2025, 1, 1)}
        recent_trial = {**ARTICLE, "pmid": "2", "publication_date": date(2026, 1, 1)}
        case = {**ARTICLE, "pmid": "3", "publication_type": ["Case Reports"]}
        self.assertEqual([item["pmid"] for item in rank_articles([recent_trial, case, guideline])], ["1", "2"])

    @override_settings(CLINICAL_EVIDENCE_GEMINI_MODEL="model", CLINICAL_EVIDENCE_SUMMARY_VERSION="v1")
    def test_no_abstract_skips_summarizer_and_existing_summary_is_reused(self):
        class FakeSummarizer:
            model = "model"; version = "v1"; calls = 0
            def summarize(self, article):
                self.calls += 1
                return {field: "x" for field in ("summary_short", "summary_objective", "summary_methods", "summary_results", "summary_clinical_significance", "summary_limitations")}
        summarizer = FakeSummarizer()
        empty = {**ARTICLE, "abstract": ""}
        evidence, _ = upsert_article(empty, "ischemic_stroke", summarizer)
        self.assertEqual(evidence.summary_status, "NO_ABSTRACT")
        self.assertEqual(summarizer.calls, 0)
        evidence, _ = upsert_article(ARTICLE, "ischemic_stroke", summarizer)
        self.assertEqual(evidence.summary_status, "READY")
        evidence, _ = upsert_article(ARTICLE, "ischemic_stroke", summarizer)
        self.assertEqual(summarizer.calls, 1)
        summarizer.version = "v2"
        evidence, _ = upsert_article(ARTICLE, "ischemic_stroke", summarizer)
        self.assertEqual(summarizer.calls, 2)

    @override_settings(CLINICAL_EVIDENCE_GEMINI_MODEL="model", CLINICAL_EVIDENCE_SUMMARY_VERSION="v1")
    def test_summary_failure_still_saves_metadata(self):
        class FailingSummarizer:
            model = "model"; version = "v1"
            def summarize(self, article): raise ExternalServiceError("FAILED")
        evidence, created = upsert_article(ARTICLE, "ischemic_stroke", FailingSummarizer())
        self.assertTrue(created)
        self.assertEqual(evidence.summary_status, "ERROR")
        self.assertEqual(evidence.title, ARTICLE["title"])


@override_settings(CLINICAL_EVIDENCE_SEARCH_LIMIT=60, CLINICAL_EVIDENCE_STORE_LIMIT=10)
class UpdateAndApiTests(TestCase):
    class Client:
        def search(self, disease): return [ARTICLE["pmid"]]
        def fetch(self, pmids): return [ARTICLE]

    class Summarizer:
        model = "model"; version = "v1"
        def summarize(self, article): raise AssertionError("disabled")

    def test_incremental_upsert_duplicate_prevention_and_disease_filter(self):
        first = update_clinical_evidence(diseases=["ischemic_stroke"], client=self.Client(), summarizer=self.Summarizer(), generate_summaries=False)
        second = update_clinical_evidence(diseases=["ischemic_stroke"], client=self.Client(), summarizer=self.Summarizer(), generate_summaries=False)
        self.assertEqual(first["status"], "SUCCESS")
        self.assertEqual(second["diseases"]["ischemic_stroke"]["inserted"], 0)
        self.assertEqual(ClinicalEvidence.objects.count(), 1)
        self.assertEqual(DiseaseEvidence.objects.filter(disease_type="ischemic_stroke", is_active=True).count(), 1)

    def test_failed_update_preserves_selection_and_success_timestamp(self):
        update_clinical_evidence(diseases=["ischemic_stroke"], client=self.Client(), summarizer=self.Summarizer(), generate_summaries=False)
        before = EvidenceUpdateState.objects.get(key="ischemic_stroke").last_success_at
        class BadClient:
            def search(self, disease): raise ExternalServiceError("UPSTREAM")
        report = update_clinical_evidence(diseases=["ischemic_stroke"], client=BadClient(), summarizer=self.Summarizer())
        self.assertEqual(report["status"], "PARTIAL_FAILURE")
        self.assertEqual(EvidenceUpdateState.objects.get(key="ischemic_stroke").last_success_at, before)
        self.assertEqual(DiseaseEvidence.objects.filter(is_active=True).count(), 1)

    def test_api_returns_top_three_and_timestamp(self):
        update_clinical_evidence(diseases=["ischemic_stroke"], client=self.Client(), summarizer=self.Summarizer(), generate_summaries=False)
        request = APIRequestFactory().get("/api/v1/clinical-evidence", {"disease": "ischemic_stroke", "limit": 3})
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        response = ClinicalEvidenceView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["disease"], "ischemic_stroke")
        self.assertEqual(response.data["items"][0]["display_rank"], 1)
        self.assertIsNotNone(response.data["updated_at"])

        all_request = APIRequestFactory().get("/api/v1/clinical-evidence", {"limit": 3})
        force_authenticate(all_request, user=SimpleNamespace(is_authenticated=True))
        all_response = ClinicalEvidenceView.as_view()(all_request)
        self.assertEqual(len(all_response.data["items"]), 3)
