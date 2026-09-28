# Generated manually for physician triage reassessment history.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TriageReview",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "reviewer_role",
                    models.CharField(
                        db_column="reviewer_role",
                        max_length=40,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        db_column="priority",
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        db_column="reason",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_column="created_at",
                        db_index=True,
                    ),
                ),
                (
                    "assessment",
                    models.ForeignKey(
                        db_column="assessment_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="triage_reviews",
                        to="assessments.initialassessment",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        db_column="reviewer_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="triage_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "triage_reviews",
                "ordering": ("created_at", "id"),
            },
        ),
        migrations.AddIndex(
            model_name="triagereview",
            index=models.Index(
                fields=["assessment", "created_at"],
                name="idx_triage_review_assess_time",
            ),
        ),
    ]
