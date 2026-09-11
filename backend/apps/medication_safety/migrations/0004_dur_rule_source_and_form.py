from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("medication_safety", "0003_medicationingredient_medication_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="durinteractionrule",
            name="source_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="durdoserule",
            name="form_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="durdoserule",
            name="source_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
