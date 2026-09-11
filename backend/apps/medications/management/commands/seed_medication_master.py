from __future__ import annotations

import hashlib
import re

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.medications.models import Medication

from apps.medication_safety.models import (
    DURAgeRule,
    DURDoseRule,
    DURDuplicateRule,
    DURDurationRule,
    DURElderlyRule,
    DURInteractionRule,
    DURPregnancyRule,
    MedicationIngredient,
)

from apps.medication_safety.services.medication_safety import (
    _form_matches,
)


def _short_hash(value):
    return hashlib.sha256(
        str(value).encode("utf-8")
    ).hexdigest()[:10]


def _ingredient_name(ingredient):
    return (
        ingredient.name_ko
        or ingredient.name_en
        or ingredient.dur_ingredient_code
    )


def _pick_form(raw):
    raw = str(raw or "").strip()

    if not raw:
        return "정제"

    candidates = []

    if len(raw) <= 50:
        candidates.append(raw)

    for value in re.split(
        r"[/,;]",
        raw,
    ):
        value = value.strip()

        if (
            value
            and len(value) <= 50
            and value not in candidates
        ):
            candidates.append(value)

    for candidate in candidates:
        if _form_matches(
            candidate,
            raw,
        ):
            return candidate

    return None


def _medication_code(
    purpose,
    identity,
):
    return (
        f"BRAINON-DEMO-{purpose}-"
        f"{_short_hash(identity)}"
    )[:50]


def _create_medication(
    *,
    purpose,
    identity,
    ingredient,
    dosage_form="정제",
):
    now = timezone.now()

    code = _medication_code(
        purpose,
        identity,
    )

    name = (
        f"BrainOn Demo {purpose} - "
        f"{_ingredient_name(ingredient)}"
    )[:200]

    medication, created = (
        Medication.objects.get_or_create(
            medication_code=code,
            defaults={
                "medication_name": name,
                "dosage_form": (
                    dosage_form
                    if dosage_form
                    else "정제"
                ),
                "strength": None,
                "manufacturer": (
                    "BrainOn Demo"
                ),
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
    )

    if not created:
        medication.medication_name = name
        medication.dosage_form = (
            dosage_form
            if dosage_form
            else "정제"
        )
        medication.strength = None
        medication.manufacturer = (
            "BrainOn Demo"
        )
        medication.is_active = True
        medication.updated_at = now

        medication.save(
            update_fields=[
                "medication_name",
                "dosage_form",
                "strength",
                "manufacturer",
                "is_active",
                "updated_at",
            ]
        )

    mapping, mapping_created = (
        MedicationIngredient.objects
        .update_or_create(
            medication=medication,
            ingredient=ingredient,
            defaults={
                "amount": None,
                "unit": None,
                "is_active": True,
            },
        )
    )

    return {
        "medication": medication,
        "created": created,
        "mapping_created": (
            mapping_created
        ),
    }


def _select_specs():

    specs = []

    # ========================================================
    # DDI: ingredient A/B
    # ========================================================

    interaction = (
        DURInteractionRule.objects
        .filter(
            is_active=True,
            ingredient_a__is_active=True,
            ingredient_b__is_active=True,
        )
        .exclude(
            ingredient_a_id=F(
                "ingredient_b_id"
            )
        )
        .select_related(
            "ingredient_a",
            "ingredient_b",
        )
        .order_by("dur_seq")
        .first()
    )

    if interaction is None:
        raise CommandError(
            "No active INTERACTION candidate."
        )

    specs.extend([
        {
            "purpose": "DDI-A",
            "identity": (
                f"{interaction.dur_seq}:A"
            ),
            "ingredient": (
                interaction.ingredient_a
            ),
            "form": "정제",
        },
        {
            "purpose": "DDI-B",
            "identity": (
                f"{interaction.dur_seq}:B"
            ),
            "ingredient": (
                interaction.ingredient_b
            ),
            "form": "정제",
        },
    ])

    # ========================================================
    # DOSE
    # ========================================================

    dose_candidate = None

    for rule in (
        DURDoseRule.objects
        .filter(
            is_active=True,
            max_dose__isnull=False,
            ingredient__is_active=True,
        )
        .select_related("ingredient")
        .order_by("dur_seq")
    ):
        form = _pick_form(
            getattr(
                rule,
                "form_name",
                "",
            )
        )

        if form:
            dose_candidate = (
                rule,
                form,
            )
            break

    if dose_candidate is None:
        raise CommandError(
            "No active DOSE candidate."
        )

    dose_rule, dose_form = (
        dose_candidate
    )

    specs.append({
        "purpose": "DOSE",
        "identity": dose_rule.dur_seq,
        "ingredient": (
            dose_rule.ingredient
        ),
        "form": dose_form,
    })

    # ========================================================
    # DUPLICATE: same therapeutic class,
    # two different ingredients
    # ========================================================

    duplicate_groups = {}

    for rule in (
        DURDuplicateRule.objects
        .filter(
            is_active=True,
            ingredient__is_active=True,
        )
        .select_related("ingredient")
        .order_by(
            "therapeutic_class_code",
            "dur_seq",
        )
    ):
        duplicate_groups.setdefault(
            rule.therapeutic_class_code,
            [],
        )

        group = duplicate_groups[
            rule.therapeutic_class_code
        ]

        if all(
            existing.ingredient_id
            != rule.ingredient_id
            for existing in group
        ):
            group.append(rule)

    duplicate_pair = None

    for class_code, rules in (
        duplicate_groups.items()
    ):
        if len(rules) >= 2:
            duplicate_pair = (
                class_code,
                rules[0],
                rules[1],
            )
            break

    if duplicate_pair is None:
        raise CommandError(
            "No active DUPLICATE pair."
        )

    class_code, dup_a, dup_b = (
        duplicate_pair
    )

    specs.extend([
        {
            "purpose": "DUP-A",
            "identity": (
                f"{class_code}:"
                f"{dup_a.dur_seq}"
            ),
            "ingredient": (
                dup_a.ingredient
            ),
            "form": "정제",
        },
        {
            "purpose": "DUP-B",
            "identity": (
                f"{class_code}:"
                f"{dup_b.dur_seq}"
            ),
            "ingredient": (
                dup_b.ingredient
            ),
            "form": "정제",
        },
    ])

    # ========================================================
    # AGE
    # ========================================================

    age_rule = (
        DURAgeRule.objects
        .filter(
            is_active=True,
            ingredient__is_active=True,
        )
        .filter(
            Q(min_age__isnull=False)
            | Q(max_age__isnull=False)
        )
        .select_related("ingredient")
        .order_by("dur_seq")
        .first()
    )

    if age_rule is None:
        raise CommandError(
            "No active AGE candidate."
        )

    specs.append({
        "purpose": "AGE",
        "identity": age_rule.dur_seq,
        "ingredient": age_rule.ingredient,
        "form": "정제",
    })

    # ========================================================
    # ELDERLY
    # ========================================================

    elderly_rule = (
        DURElderlyRule.objects
        .filter(
            is_active=True,
            ingredient__is_active=True,
            age_threshold=65,
        )
        .select_related("ingredient")
        .order_by("dur_seq")
        .first()
    )

    if elderly_rule is None:
        raise CommandError(
            "No active ELDERLY candidate."
        )

    specs.append({
        "purpose": "ELDERLY",
        "identity": elderly_rule.dur_seq,
        "ingredient": (
            elderly_rule.ingredient
        ),
        "form": "정제",
    })

    # ========================================================
    # PREGNANCY
    # ========================================================

    pregnancy_rule = (
        DURPregnancyRule.objects
        .filter(
            is_active=True,
            ingredient__is_active=True,
        )
        .select_related("ingredient")
        .order_by("dur_seq")
        .first()
    )

    if pregnancy_rule is None:
        raise CommandError(
            "No active PREGNANCY candidate."
        )

    specs.append({
        "purpose": "PREGNANCY",
        "identity": (
            pregnancy_rule.dur_seq
        ),
        "ingredient": (
            pregnancy_rule.ingredient
        ),
        "form": "정제",
    })

    # ========================================================
    # DURATION
    # ========================================================

    duration_candidate = None

    for rule in (
        DURDurationRule.objects
        .filter(
            is_active=True,
            max_duration_days__isnull=False,
            ingredient__is_active=True,
        )
        .select_related("ingredient")
        .order_by("dur_seq")
    ):
        form = _pick_form(
            rule.form_name
        )

        if form:
            duration_candidate = (
                rule,
                form,
            )
            break

    if duration_candidate is None:
        raise CommandError(
            "No active DURATION candidate."
        )

    duration_rule, duration_form = (
        duration_candidate
    )

    specs.append({
        "purpose": "DURATION",
        "identity": (
            duration_rule.dur_seq
        ),
        "ingredient": (
            duration_rule.ingredient
        ),
        "form": duration_form,
    })

    return specs


class Command(BaseCommand):
    help = (
        "Seed deterministic BrainOn demo "
        "Medication Master and ingredient mappings."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        dry_run = bool(
            options["dry_run"]
        )

        with transaction.atomic():

            specs = _select_specs()

            created = 0
            updated = 0
            mapping_created = 0

            rows = []

            for spec in specs:

                result = (
                    _create_medication(
                        purpose=(
                            spec["purpose"]
                        ),
                        identity=(
                            spec["identity"]
                        ),
                        ingredient=(
                            spec["ingredient"]
                        ),
                        dosage_form=(
                            spec["form"]
                        ),
                    )
                )

                medication = (
                    result["medication"]
                )

                if result["created"]:
                    created += 1
                else:
                    updated += 1

                if result[
                    "mapping_created"
                ]:
                    mapping_created += 1

                rows.append({
                    "purpose": (
                        spec["purpose"]
                    ),
                    "medication_code": (
                        medication.medication_code
                    ),
                    "medication_id": str(
                        medication.id
                    ),
                    "ingredient_code": (
                        spec["ingredient"]
                        .dur_ingredient_code
                    ),
                    "ingredient_name": (
                        _ingredient_name(
                            spec["ingredient"]
                        )
                    ),
                    "dosage_form": (
                        medication.dosage_form
                    ),
                })

            self.stdout.write(
                "MEDICATION_MASTER_SEED:"
            )

            for row in rows:
                self.stdout.write(
                    str(row)
                )

            self.stdout.write(
                (
                    "SUMMARY: "
                    f"medications={len(rows)} "
                    f"created={created} "
                    f"updated={updated} "
                    f"mapping_created="
                    f"{mapping_created}"
                )
            )

            if dry_run:
                transaction.set_rollback(
                    True
                )

                self.stdout.write(
                    "DB_WRITE: NO"
                )

            else:
                self.stdout.write(
                    "MEDICATION_MASTER_SEED_OK"
                )
