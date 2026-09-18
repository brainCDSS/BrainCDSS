import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("consultations", "0002_consultation_message"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ConsultationChatPresence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_seen_at", models.DateTimeField()),
                ("is_typing", models.BooleanField(default=False)),
                ("typing_updated_at", models.DateTimeField(blank=True, null=True)),
                ("consultation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_presences", to="consultations.consultation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consultation_chat_presences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "consultation_chat_presences"},
        ),
        migrations.AddConstraint(model_name="consultationchatpresence", constraint=models.UniqueConstraint(fields=("consultation", "user"), name="uq_consultation_chat_presence")),
        migrations.AddIndex(model_name="consultationchatpresence", index=models.Index(fields=["consultation", "last_seen_at"], name="consult_chat_presence_seen_idx")),
    ]
