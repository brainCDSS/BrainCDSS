import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppointmentRescheduleHistory",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_column="id",
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "rescheduled_at",
                    models.DateTimeField(
                        db_column="rescheduled_at",
                        db_index=True,
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "reschedule_reason",
                    models.CharField(
                        blank=True,
                        db_column="reschedule_reason",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "appointment",
                    models.ForeignKey(
                        db_column="appointment_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reschedule_history",
                        to="appointments.appointment",
                    ),
                ),
                (
                    "previous_slot",
                    models.ForeignKey(
                        db_column="previous_slot_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="appointments.appointmentslot",
                    ),
                ),
                (
                    "changed_slot",
                    models.ForeignKey(
                        db_column="changed_slot_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="appointments.appointmentslot",
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="changed_by_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "appointment_reschedule_history",
                "ordering": ["-rescheduled_at"],
            },
        ),
    ]
