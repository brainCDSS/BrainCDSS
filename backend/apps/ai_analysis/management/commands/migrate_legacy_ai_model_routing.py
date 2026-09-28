"""Copy AI model routing metadata from a legacy PostgreSQL database.

The command intentionally excludes patient-specific analysis and result tables.
It is safe to run repeatedly: existing identical records are retained, while
conflicting records stop the operation rather than being overwritten.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

import psycopg
from psycopg.rows import dict_row
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.ai_analysis.models import (
    AIModel,
    AIModelConfigVersion,
    AIRoutingConfigVersion,
    ModelVersion,
)


MODEL_FIELDS = (
    "id", "code", "display_name", "task_type", "disease_scope",
    "supported_modalities", "description", "is_enabled", "created_at", "updated_at",
)
VERSION_FIELDS = (
    "id", "model_id", "version", "mlflow_registered_model_name",
    "mlflow_model_version", "mlflow_run_id", "artifact_uri",
    "container_image_digest", "code_commit_sha", "input_contract",
    "output_contract", "preprocessing_config", "validation_status", "is_active",
    "performance_metrics", "created_at", "updated_at",
)
CONFIG_FIELDS = (
    "id", "model_version_id", "config_version", "threshold_config", "is_active", "created_at",
)
ROUTING_FIELDS = (
    "id", "version", "modality", "analysis_type", "target_model_version_id", "is_active", "created_at",
)


def _select(table: str, fields: Iterable[str]) -> str:
    return f"SELECT {', '.join(fields)} FROM {table} ORDER BY created_at, id"


class Command(BaseCommand):
    help = "Copy legacy AI model, version, config, and routing records without patient data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-db",
            default=os.getenv("LEGACY_POSTGRES_DB", "brainon"),
            help="Legacy PostgreSQL database name (default: LEGACY_POSTGRES_DB or brainon).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write records to the current Django database. Without this flag, only validate and report.",
        )

    def _legacy_rows(self, source_db: str, table: str, fields: Iterable[str]):
        connection_kwargs = {
            "dbname": source_db,
            "user": os.environ.get("POSTGRES_USER", ""),
            "password": os.environ.get("POSTGRES_PASSWORD", ""),
            "host": os.environ.get("POSTGRES_HOST", ""),
            "port": os.environ.get("POSTGRES_PORT", "5432"),
            "row_factory": dict_row,
        }
        if not all(connection_kwargs[key] for key in ("dbname", "user", "password", "host")):
            raise CommandError("Legacy database connection settings are incomplete.")
        try:
            with psycopg.connect(**connection_kwargs) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_select(table, fields))
                    return list(cursor.fetchall())
        except psycopg.Error as exc:
            raise CommandError("Could not read the legacy model metadata database.") from exc

    @staticmethod
    def _same(instance, values: dict, fields: Iterable[str]) -> bool:
        return all(getattr(instance, field) == values[field] for field in fields)

    def handle(self, *args, **options):
        source_db = options["source_db"]
        target_db = os.environ.get("POSTGRES_DB", "")
        if source_db == target_db:
            raise CommandError("Source and target database must be different.")

        legacy_models = self._legacy_rows(source_db, "ai_aimodel", MODEL_FIELDS)
        legacy_versions = self._legacy_rows(source_db, "ai_modelversion", VERSION_FIELDS)
        legacy_configs = self._legacy_rows(source_db, "ai_modelconfigversion", CONFIG_FIELDS)
        legacy_routings = self._legacy_rows(source_db, "ai_airoutingconfigversion", ROUTING_FIELDS)

        self.stdout.write(
            f"SOURCE {source_db}: models={len(legacy_models)} versions={len(legacy_versions)} "
            f"configs={len(legacy_configs)} routings={len(legacy_routings)}"
        )
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("DRY RUN: no target data was written. Re-run with --apply to migrate."))
            return

        model_map: dict[object, AIModel] = {}
        version_map: dict[object, ModelVersion] = {}
        created = {"models": 0, "versions": 0, "configs": 0, "routings": 0}

        with transaction.atomic():
            for row in legacy_models:
                existing = AIModel.objects.filter(code=row["code"]).first()
                if existing is None:
                    model = AIModel.objects.create(**row)
                    created["models"] += 1
                elif self._same(existing, row, MODEL_FIELDS[1:]):
                    model = existing
                else:
                    raise CommandError(f"Conflicting target AIModel code: {row['code']}")
                model_map[row["id"]] = model

            for row in legacy_versions:
                values = dict(row)
                source_model_id = values.pop("model_id")
                values["mlflow_run"] = values.pop("mlflow_run_id")
                model = model_map.get(source_model_id)
                if model is None:
                    raise CommandError("Legacy ModelVersion references an unknown AIModel.")
                values["model"] = model
                existing = ModelVersion.objects.filter(model=model, version=values["version"]).first()
                compare_fields = (
                    "version", "mlflow_registered_model_name", "mlflow_model_version",
                    "mlflow_run", "artifact_uri", "container_image_digest", "code_commit_sha",
                    "input_contract", "output_contract", "preprocessing_config", "validation_status",
                    "is_active", "performance_metrics", "created_at", "updated_at",
                )
                if existing is None:
                    version = ModelVersion.objects.create(**values)
                    created["versions"] += 1
                elif self._same(existing, values, compare_fields):
                    version = existing
                else:
                    raise CommandError(f"Conflicting target ModelVersion: {model.code}/{values['version']}")
                version_map[row["id"]] = version

            for row in legacy_configs:
                values = dict(row)
                source_version_id = values.pop("model_version_id")
                version = version_map.get(source_version_id)
                if version is None:
                    raise CommandError("Legacy model configuration references an unknown ModelVersion.")
                values["model_version"] = version
                existing = AIModelConfigVersion.objects.filter(
                    model_version=version, config_version=values["config_version"]
                ).first()
                compare_fields = tuple(field for field in CONFIG_FIELDS if field not in {"id", "model_version_id"})
                if existing is None:
                    AIModelConfigVersion.objects.create(**values)
                    created["configs"] += 1
                elif not self._same(existing, values, compare_fields):
                    raise CommandError(f"Conflicting target model config: {version.version}/{values['config_version']}")

            for row in legacy_routings:
                values = dict(row)
                source_version_id = values.pop("target_model_version_id")
                values["target_model_version"] = version_map.get(source_version_id)
                if source_version_id is not None and values["target_model_version"] is None:
                    raise CommandError("Legacy routing references an unknown ModelVersion.")
                existing = AIRoutingConfigVersion.objects.filter(version=values["version"]).first()
                compare_fields = tuple(field for field in ROUTING_FIELDS if field not in {"id", "target_model_version_id"})
                if existing is None:
                    AIRoutingConfigVersion.objects.create(**values)
                    created["routings"] += 1
                elif (
                    not self._same(existing, values, compare_fields)
                    or existing.target_model_version_id != getattr(values["target_model_version"], "id", None)
                ):
                    raise CommandError(f"Conflicting target routing version: {values['version']}")

        self.stdout.write(self.style.SUCCESS(
            "MIGRATED " + " ".join(f"{name}={count}" for name, count in created.items())
        ))
