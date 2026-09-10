import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.imaging.models import NiftiArtifact, SeriesReference
from apps.imaging.services.nifti import parse_allowed_gcs_uri


class Command(BaseCommand):
    help = "Register an explicit non-PHI series-to-GCS NIfTI manifest."

    def add_arguments(self, parser):
        parser.add_argument("manifest", type=Path)

    def handle(self, *args, **options):
        items = json.loads(options["manifest"].read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise CommandError("Manifest root must be a list")
        for item in items:
            parse_allowed_gcs_uri(item["uri"])
            series = SeriesReference.objects.filter(pk=item["series_id"]).first()
            if series is None:
                raise CommandError(f"Unknown series_id: {item['series_id']}")
            NiftiArtifact.objects.update_or_create(
                series=series,
                defaults={
                    "role": item["role"], "uri": item["uri"],
                    "size_bytes": item["size_bytes"], "sha256": item["sha256"],
                    "source": item.get("source", "PROTOTYPE_GCS"),
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Registered {len(items)} NIfTI artifacts"))
