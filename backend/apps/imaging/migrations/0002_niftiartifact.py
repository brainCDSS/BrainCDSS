import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("imaging", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="NiftiArtifact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("CT", "CT"), ("DWI", "DWI"), ("ADC", "ADC"), ("MRA", "MRA")], db_index=True, max_length=16)),
                ("uri", models.CharField(max_length=1024, unique=True)),
                ("size_bytes", models.BigIntegerField()),
                ("sha256", models.CharField(max_length=64)),
                ("source", models.CharField(default="DICOM_CONVERSION", max_length=24)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("series", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="nifti_artifact", to="imaging.seriesreference")),
            ],
            options={"db_table": "imaging_niftiartifact"},
        )
    ]
