from django.core.management.base import BaseCommand

from apps.medications.disease_group_catalog import (
    DISEASE_GROUP_MEDICATION_CODES,
    MAPPING_EVIDENCE_SOURCE,
)
from apps.medications.models import Medication, MedicationDiseaseGroup


class Command(BaseCommand):
    help = "Idempotently sync curated medication disease-group mappings."

    def handle(self, *args, **options):
        created = updated = 0
        missing = []
        for disease_group, codes in DISEASE_GROUP_MEDICATION_CODES.items():
            medications = {
                item.medication_code: item
                for item in Medication.objects.filter(medication_code__in=codes)
            }
            for code in codes:
                medication = medications.get(code)
                if medication is None:
                    missing.append(code)
                    continue
                _mapping, was_created = MedicationDiseaseGroup.objects.update_or_create(
                    medication=medication,
                    disease_group=disease_group,
                    defaults={
                        "is_active": True,
                        "evidence_source": MAPPING_EVIDENCE_SOURCE,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(
            f"created={created} updated={updated} missing={len(missing)}"
        ))
        if missing:
            self.stdout.write("missing_codes=" + ",".join(missing))
