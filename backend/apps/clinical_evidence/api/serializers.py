from rest_framework import serializers

from ..config import DISEASE_QUERIES
from ..models import ClinicalEvidence


class EvidenceQuerySerializer(serializers.Serializer):
    disease = serializers.ChoiceField(choices=tuple(DISEASE_QUERIES), required=False)
    limit = serializers.IntegerField(min_value=1, max_value=10, default=3)


class ClinicalEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalEvidence
        fields = ["pmid", "title", "journal", "authors", "publication_date", "publication_year",
            "publication_type", "summary_short", "summary_objective", "summary_methods", "summary_results",
            "summary_clinical_significance", "summary_limitations", "summary_source", "summary_model",
            "summary_generated_at", "summary_status", "pubmed_url", "doi", "pmcid", "display_rank"]
