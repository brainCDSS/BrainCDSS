import json

from django.core.management.base import BaseCommand, CommandError

from ...config import DISEASE_QUERIES
from ...services.pubmed import PubMedClient
from ...services.ranking import rank_articles
from ...services.update import update_clinical_evidence


class Command(BaseCommand):
    help = "Refresh curated PubMed evidence and pre-generate independent Vertex summaries."

    def add_arguments(self, parser):
        parser.add_argument("--disease", choices=tuple(DISEASE_QUERIES))
        parser.add_argument("--no-summaries", action="store_true", help="Store metadata without Vertex calls.")
        parser.add_argument("--dry-run", action="store_true", help="Read PubMed only; no DB writes or Vertex calls.")

    def handle(self, *args, **options):
        diseases = (options["disease"],) if options["disease"] else tuple(DISEASE_QUERIES)
        if options["dry_run"]:
            client = PubMedClient()
            try:
                result = {}
                for disease in diseases:
                    pmids = client.search(disease)
                    metadata = client.fetch(pmids)
                    ranked = rank_articles(metadata, disease)
                    result[disease] = {"search_count": len(pmids), "parsed_count": len(metadata),
                        "ranked_count": len(ranked), "items": [{"pmid": row["pmid"], "title": row["title"],
                        "publication_type": row["publication_type"]} for row in ranked[:3]]}
            except Exception:
                raise CommandError("PUBMED_DRY_RUN_FAILED") from None
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
            return
        report = update_clinical_evidence(diseases=diseases, generate_summaries=not options["no_summaries"])
        self.stdout.write(json.dumps(report, ensure_ascii=False))
        if report["status"] == "PARTIAL_FAILURE":
            raise CommandError("CLINICAL_EVIDENCE_PARTIAL_FAILURE")
