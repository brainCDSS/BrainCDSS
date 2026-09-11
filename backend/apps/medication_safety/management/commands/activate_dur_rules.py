import json

from django.core.management.base import BaseCommand

from apps.medication_safety.services.dur_activation import (
    apply_dur_activation_policy,
)


class Command(BaseCommand):
    help = (
        "Apply BrainOn runtime activation policy "
        "to synchronized DUR rules."
    )

    def handle(self, *args, **options):
        result = apply_dur_activation_policy()

        self.stdout.write(
            "DUR_ACTIVATION_RESULT: "
            + json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "DUR_ACTIVATION_OK"
            )
        )
