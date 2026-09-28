import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("medications", "0002_initial")]

    operations = [
        migrations.CreateModel(
            name="MedicationDiseaseGroup",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("disease_group", models.CharField(choices=[("HEMORRHAGIC_STROKE", "뇌출혈"), ("ISCHEMIC_STROKE", "뇌경색"), ("CEREBRAL_ANEURYSM", "뇌동맥류")], db_index=True, max_length=32)),
                ("evidence_source", models.CharField(blank=True, max_length=500)),
                ("note", models.CharField(blank=True, max_length=500)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("medication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="disease_groups", to="medications.medication")),
            ],
            options={
                "db_table": "medication_disease_groups",
                "constraints": [models.UniqueConstraint(fields=("medication", "disease_group"), name="uq_medication_disease_group")],
            },
        ),
    ]
