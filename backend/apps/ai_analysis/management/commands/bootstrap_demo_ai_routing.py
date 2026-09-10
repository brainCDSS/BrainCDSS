from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import AIModel, AIModelConfigVersion, AIRoutingConfigVersion, ModelVersion


MODELS = (
    {
        "code": "H-N00", "name": "Hemorrhagic Stroke CT", "scope": "HEMORRHAGE",
        "modalities": ["CT"], "analysis_type": "HEMORRHAGIC_STROKE_CT",
        "artifact_uri": "gs://brainon-cdss-models/hemorrhagic-stroke-ct/H-N00/manifest.json",
    },
    {
        "code": "I-N00", "name": "Ischemic Stroke DWI ADC", "scope": "ISCHEMIA",
        "modalities": ["MR"], "analysis_type": "ISCHEMIC_STROKE_DWI_ADC",
        "artifact_uri": "gs://brainon-cdss-models/ischemic-stroke-dwi-adc/I-N00/manifest.json",
    },
    {
        "code": "A-N00", "name": "Cerebral Aneurysm MRA", "scope": "ANEURYSM",
        "modalities": ["MR"], "analysis_type": "CEREBRAL_ANEURYSM_MRA",
        "artifact_uri": "gs://brainon-cdss-models/cerebral-aneurysm-mra/A-N00/manifest.json",
    },
)


class Command(BaseCommand):
    help = "Register the three approved demo model routes backed by GCS manifests."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        for item in MODELS:
            model, _ = AIModel.objects.update_or_create(
                code=item["code"],
                defaults={
                    "display_name": item["name"], "task_type": "SEGMENTATION",
                    "disease_scope": item["scope"], "supported_modalities": item["modalities"],
                    "description": "Prototype runtime model registered from a verified GCS manifest.",
                    "is_enabled": True, "created_at": now, "updated_at": now,
                },
            )
            ModelVersion.objects.filter(model=model).update(is_active=False)
            version, _ = ModelVersion.objects.update_or_create(
                model=model, version=item["code"],
                defaults={
                    "mlflow_registered_model_name": item["code"], "mlflow_model_version": "UNREGISTERED",
                    "mlflow_run": "UNREGISTERED", "artifact_uri": item["artifact_uri"],
                    "container_image_digest": "brainon-inference:2026-09-09",
                    "code_commit_sha": "UNREGISTERED", "input_contract": {"analysis_type": item["analysis_type"]},
                    "output_contract": {"schema_version": "1.0", "artifacts": ["NIFTI_MASK", "RESULT_JSON"]},
                    "preprocessing_config": {"source": "GCS_MANIFEST"},
                    "validation_status": "APPROVED", "is_active": True,
                    "performance_metrics": {"demo_registration": True}, "created_at": now, "updated_at": now,
                },
            )
            AIModelConfigVersion.objects.filter(model_version=version).update(is_active=False)
            AIModelConfigVersion.objects.update_or_create(
                model_version=version, config_version="demo-v1",
                defaults={"threshold_config": {"threshold": 0.5}, "is_active": True, "created_at": now},
            )
            AIRoutingConfigVersion.objects.filter(analysis_type=item["analysis_type"]).update(is_active=False)
            AIRoutingConfigVersion.objects.update_or_create(
                version=f"demo-{item['code']}",
                defaults={
                    "modality": item["modalities"][0], "analysis_type": item["analysis_type"],
                    "target_model_version": version, "is_active": True, "created_at": now,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Activated {item['analysis_type']} -> {item['code']}"))
