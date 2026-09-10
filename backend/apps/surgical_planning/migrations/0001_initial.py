import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("patients", "0001_initial"),
        ("clinical_records", "0001_initial"),
        ("imaging", "0001_initial"),
        ("ai_analysis", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SurgicalPlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("IN_PROGRESS", "In progress"), ("REVIEW_REQUESTED", "Review requested"), ("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled")], db_index=True, default="DRAFT", max_length=20)),
                ("version", models.PositiveIntegerField(default=1)),
                ("treatment_type", models.CharField(blank=True, max_length=100)),
                ("memo", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("ai_analysis", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="surgical_plans", to="ai_analysis.aianalysis")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_surgical_plans", to=settings.AUTH_USER_MODEL)),
                ("encounter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="surgical_plans", to="clinical_records.encounter")),
                ("finalized_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="finalized_surgical_plans", to=settings.AUTH_USER_MODEL)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="surgical_plans", to="patients.patient")),
                ("study", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="surgical_plans", to="imaging.imagingstudy")),
            ],
            options={"db_table": "surgical_plans", "ordering": ("-updated_at",)},
        ),
        migrations.CreateModel(
            name="SurgicalPlanClip",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("clip_id", models.CharField(max_length=100)),
                ("clip_type", models.CharField(max_length=50)),
                ("size", models.DecimalField(decimal_places=3, max_digits=10)),
                ("position_x", models.DecimalField(decimal_places=4, max_digits=12)),
                ("position_y", models.DecimalField(decimal_places=4, max_digits=12)),
                ("position_z", models.DecimalField(decimal_places=4, max_digits=12)),
                ("rotation_x", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("rotation_y", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("rotation_z", models.DecimalField(decimal_places=4, default=0, max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("planning", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="clips", to="surgical_planning.surgicalplan")),
            ],
            options={"db_table": "surgical_plan_clips", "ordering": ("created_at",)},
        ),
        migrations.CreateModel(
            name="SurgicalPlanMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("message", models.TextField()),
                ("viewer_state", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("planning", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="surgical_planning.surgicalplan")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="surgical_plan_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "surgical_plan_messages", "ordering": ("created_at",)},
        ),
    ]
