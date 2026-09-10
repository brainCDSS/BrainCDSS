"""ai_analysis persistence models; TODO after domain schema approval."""

import uuid

from django.db import models

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import AIModel, ModelVersion, AIAnalysis, AIAnalysisInputSeries, AIAnalysisAttempt, AIAnalysisResult, AIResultReview, AIModelConfigVersion, AIRoutingConfigVersion, AIAnalysisStatusHistory, AIResultArtifact
# === FINAL_DB_GENERATED_IMPORTS_END ===


class AIAnalysisInputArtifact(models.Model):
    """Immutable NIfTI object selected for a concrete analysis attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(AIAnalysis, on_delete=models.CASCADE, related_name="input_artifacts")
    role = models.CharField(max_length=16, db_index=True)
    uri = models.CharField(max_length=1024)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)

    class Meta:
        db_table = "ai_aianalysisinputartifact"
        constraints = [
            models.UniqueConstraint(fields=("analysis", "role"), name="uq_analysis_input_role")
        ]
