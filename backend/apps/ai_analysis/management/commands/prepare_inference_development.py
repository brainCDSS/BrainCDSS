"""Create clearly labelled synthetic references for local inference checks."""

import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.ai_analysis.models import AIModel, AIModelConfigVersion, ModelVersion
from apps.imaging.models import ImagingStudy


class Command(BaseCommand):
    help = "Prepare non-clinical references for the local inference bridge."

    def handle(self, *args, **options):
        now = timezone.now()
        role, _ = Role.objects.get_or_create(
            code="RADIOLOGY",
            defaults={"name": "Radiology", "is_active": True},
        )
        user, created = User.objects.get_or_create(
            login_id="synthetic-inference-user",
            defaults={
                "name": "Synthetic Inference User",
                "role": role,
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        study, _ = ImagingStudy.objects.get_or_create(
            study_instance_uid="1.2.826.0.1.3680043.10.999.1001",
            defaults={
                "patient": None,
                "imaging_order": None,
                "accession_number": "SYNTHETIC-INFERENCE-ONLY",
                "orthanc_study": None,
                "study_datetime": now,
                "modalities": ["CT"],
                "study_description": "Synthetic inference bridge input",
                "series_count": 0,
                "instance_count": 0,
                "status": "AVAILABLE",
                "last_synced_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )
        model, _ = AIModel.objects.get_or_create(
            code="synthetic-inference-mock",
            defaults={
                "display_name": "Synthetic Inference Mock",
                "task_type": "MOCK",
                "disease_scope": "NONE",
                "supported_modalities": ["CT"],
                "description": "No weights; local integration checks only",
                "is_enabled": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        version, _ = ModelVersion.objects.get_or_create(
            model=model,
            version="MOCK-1",
            defaults={
                "mlflow_registered_model_name": "MOCK",
                "mlflow_model_version": "0",
                "mlflow_run": "MOCK",
                "artifact_uri": "MOCK",
                "container_image_digest": "MOCK",
                "code_commit_sha": "MOCK",
                "input_contract": {},
                "output_contract": {"schema_version": "MOCK"},
                "preprocessing_config": {},
                "validation_status": "APPROVED",
                "is_active": True,
                "performance_metrics": {"accuracy_simulated": False},
                "created_at": now,
                "updated_at": now,
            },
        )
        config, _ = AIModelConfigVersion.objects.get_or_create(
            model_version=version,
            config_version="MOCK-1",
            defaults={
                "threshold_config": {},
                "is_active": True,
                "created_at": now,
            },
        )
        self.stdout.write(json.dumps({
            "study_id": str(study.id),
            "model_version_id": str(version.id),
            "model_config_version_id": str(config.id),
            "requested_by_id": str(user.id),
        }))
