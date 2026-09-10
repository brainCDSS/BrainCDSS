import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai_analysis", "0002_initial")]

    operations = [
        migrations.CreateModel(
            name="AIAnalysisInputArtifact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(db_index=True, max_length=16)),
                ("uri", models.CharField(max_length=1024)),
                ("size_bytes", models.BigIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("analysis", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="input_artifacts", to="ai_analysis.aianalysis")),
            ],
            options={"db_table": "ai_aianalysisinputartifact"},
        ),
        migrations.AddConstraint(
            model_name="aianalysisinputartifact",
            constraint=models.UniqueConstraint(fields=("analysis", "role"), name="uq_analysis_input_role"),
        ),
    ]
