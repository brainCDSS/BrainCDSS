"""Runtime medication safety evaluation.

Implemented rule types:
- DDI
- DOSE
- DUPLICATE
- AGE
- ELDERLY
- PREGNANCY
- ALLERGY

Runtime evaluation uses the local PostgreSQL DUR database only.
External DUR APIs are never called here.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.medications.models import Medication
from apps.medication_safety.models import (
    MedicationIngredient,
    PatientAllergy,
    DURInteractionRule,
    DURDoseRule,
    DURDuplicateRule,
    DURAgeRule,
    DURElderlyRule,
    DURPregnancyRule,
    DURDurationRule,
)


UNIT_ALIASES = {
    "mg": "mg",
    "㎎": "mg",
    "밀리그램": "mg",

    "g": "g",
    "gram": "g",
    "그램": "g",

    "mcg": "mcg",
    "ug": "mcg",
    "μg": "mcg",
    "㎍": "mcg",
    "마이크로그램": "mcg",
}


TO_MG = {
    "mg": Decimal("1"),
    "g": Decimal("1000"),
    "mcg": Decimal("0.001"),
}


class MedicationSafetyError(Exception):
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _normalize_unit(value):
    unit = str(value or "").strip()

    normalized = UNIT_ALIASES.get(
        unit.lower()
    )

    if normalized is None:
        normalized = UNIT_ALIASES.get(unit)

    if normalized is None:
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_UNIT_INVALID",
            f"Unsupported dose unit: {value}",
        )

    return normalized


def _positive_decimal(value, field):
    try:
        result = Decimal(str(value))
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            f"{field} must be numeric.",
        )

    if result <= 0:
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            f"{field} must be greater than zero.",
        )

    return result


def _positive_int(value, field):
    if isinstance(value, bool):
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            f"{field} must be an integer.",
        )

    try:
        result = int(value)
    except (ValueError, TypeError):
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            f"{field} must be an integer.",
        )

    if result <= 0:
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            f"{field} must be greater than zero.",
        )

    return result


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            f"Invalid medication_id: {value}",
        )


def _form_matches(
    medication_form,
    rule_form,
):
    medication_form = (
        str(medication_form or "")
        .strip()
        .replace(" ", "")
    )

    rule_form = (
        str(rule_form or "")
        .strip()
        .replace(" ", "")
    )

    if not medication_form or not rule_form:
        return True

    return (
        medication_form in rule_form
        or rule_form in medication_form
    )


def _patient_age(patient):
    if patient is None:
        return None

    if patient.birth_date:
        today = timezone.localdate()

        return (
            today.year
            - patient.birth_date.year
            - (
                (today.month, today.day)
                < (
                    patient.birth_date.month,
                    patient.birth_date.day,
                )
            )
        )

    return patient.estimated_age


def _age_rule_matches(rule, age):
    if age is None:
        return False

    if (
        rule.min_age is not None
        and age < rule.min_age
    ):
        return False

    if (
        rule.max_age is not None
        and age > rule.max_age
    ):
        return False

    return (
        rule.min_age is not None
        or rule.max_age is not None
    )


def _normalized_text(value):
    return (
        str(value or "")
        .strip()
        .casefold()
    )


def _active_current_medication_ids(patient):
    """
    CURRENT_MEDICATION_RELATION_CONTEXT_V1

    FINAL 처방 중 오늘 실제 복용 기간에 포함되는 약물만
    DDI / DUPLICATE 관계 검사 context로 사용한다.
    """
    if patient is None:
        return set()

    # prescriptions -> medication_safety circular import 방지
    from apps.prescriptions.models import PrescriptionItem

    today = timezone.localdate()

    rows = (
        PrescriptionItem.objects
        .filter(
            prescription__encounter__patient_id=patient.id,
            prescription__status="FINAL",
            start_date__lte=today,
            duration_days__gt=0,
        )
        .values(
            "medication_id",
            "start_date",
            "duration_days",
        )
    )

    medication_ids = set()

    for row in rows:
        end_date = (
            row["start_date"]
            + timedelta(
                days=int(row["duration_days"])
            )
        )

        # CurrentMedicationsView와 동일한 기간 판정.
        if today < end_date:
            medication_ids.add(
                row["medication_id"]
            )

    return medication_ids


def check_medication_safety(
    *,
    medications,
    patient=None,
):
    if (
        not isinstance(medications, list)
        or not medications
    ):
        raise MedicationSafetyError(
            "MEDICATION_SAFETY_INPUT_INVALID",
            "medications must contain at least one item.",
        )

    normalized = []

    for index, item in enumerate(medications):
        if not isinstance(item, dict):
            raise MedicationSafetyError(
                "MEDICATION_SAFETY_INPUT_INVALID",
                (
                    f"medications[{index}] "
                    "must be an object."
                ),
            )

        medication_id = _uuid(
            item.get("medication_id")
        )

        dose = _positive_decimal(
            item.get("dose"),
            f"medications[{index}].dose",
        )

        frequency = _positive_int(
            item.get("frequency_per_day"),
            (
                f"medications[{index}]"
                ".frequency_per_day"
            ),
        )

        unit = _normalize_unit(
            item.get("unit")
            or item.get("dose_unit")
        )

        duration_raw = item.get(
            "duration_days"
        )

        duration_days = None

        if duration_raw not in (
            None,
            "",
        ):
            duration_days = _positive_int(
                duration_raw,
                (
                    f"medications[{index}]"
                    ".duration_days"
                ),
            )

        normalized.append(
            {
                "medication_id": medication_id,
                "dose": dose,
                "unit": unit,
                "frequency_per_day": frequency,
                "duration_days": duration_days,
                "route": item.get("route"),
            }
        )

    medication_ids = {
        item["medication_id"]
        for item in normalized
    }

    medication_objects = {
        obj.id: obj
        for obj in (
            Medication.objects
            .filter(
                id__in=medication_ids,
                is_active=True,
            )
        )
    }

    missing = (
        medication_ids
        - set(medication_objects)
    )

    if missing:
        raise MedicationSafetyError(
            "MEDICATION_NOT_FOUND",
            (
                "Active medication not found: "
                + ", ".join(
                    sorted(
                        str(value)
                        for value in missing
                    )
                )
            ),
        )

    mappings = list(
        MedicationIngredient.objects
        .filter(
            medication_id__in=medication_ids,
            medication__is_active=True,
            ingredient__is_active=True,
            is_active=True,
        )
        .select_related(
            "medication",
            "ingredient",
        )
    )

    mappings_by_medication = defaultdict(
        list
    )

    ingredient_to_medications = defaultdict(
        set
    )

    ingredient_objects = {}

    for mapping in mappings:
        mappings_by_medication[
            mapping.medication_id
        ].append(mapping)

        ingredient_to_medications[
            mapping.ingredient_id
        ].add(mapping.medication_id)

        ingredient_objects[
            mapping.ingredient_id
        ] = mapping.ingredient

    for medication_id in medication_ids:
        count = len(
            mappings_by_medication[
                medication_id
            ]
        )

        if count == 0:
            raise MedicationSafetyError(
                (
                    "MEDICATION_INGREDIENT_"
                    "MAPPING_MISSING"
                ),
                (
                    "No active ingredient mapping "
                    f"for medication {medication_id}"
                ),
            )

        # 현재 DOSE importer는 단일 성분 기준이므로
        # 복합제 용량을 임의 분배하지 않는다.
        if count != 1:
            raise MedicationSafetyError(
                (
                    "MEDICATION_MULTI_INGREDIENT_"
                    "UNSUPPORTED"
                ),
                (
                    "Current runtime dose safety "
                    "supports one active ingredient "
                    "mapping per medication."
                ),
            )

    ingredient_ids = set(
        ingredient_to_medications
    )

    # --------------------------------------------------------
    # 기존 복용약은 DDI / DUPLICATE 관계 검사에만 포함.
    # 다른 Safety rule의 평가 대상은 확장하지 않는다.
    # --------------------------------------------------------

    current_medication_ids = (
        _active_current_medication_ids(
            patient
        )
    )

    relationship_medication_ids = (
        medication_ids
        | current_medication_ids
    )

    relationship_mappings = list(
        MedicationIngredient.objects
        .filter(
            medication_id__in=
                relationship_medication_ids,
            medication__is_active=True,
            ingredient__is_active=True,
            is_active=True,
        )
    )

    relationship_ingredient_to_medications = (
        defaultdict(set)
    )

    for mapping in relationship_mappings:
        relationship_ingredient_to_medications[
            mapping.ingredient_id
        ].add(
            mapping.medication_id
        )

    relationship_ingredient_ids = set(
        relationship_ingredient_to_medications
    )

    alerts = []

    # =========================================================
    # 1. DDI
    # =========================================================

    interaction_rules = (
        DURInteractionRule.objects
        .filter(
            is_active=True,
            ingredient_a_id__in=
                relationship_ingredient_ids,
            ingredient_b_id__in=
                relationship_ingredient_ids,
        )
        .select_related(
            "ingredient_a",
            "ingredient_b",
        )
    )

    for rule in interaction_rules:
        related_ids = (
            relationship_ingredient_to_medications[
                rule.ingredient_a_id
            ]
            | relationship_ingredient_to_medications[
                rule.ingredient_b_id
            ]
        )

        if len(related_ids) < 2:
            continue

        # 현재 복용약끼리만 존재하던 기존 DDI는
        # 이번 신규 처방의 경고로 다시 보여주지 않는다.
        if not (
            related_ids
            & medication_ids
        ):
            continue

        related = sorted(
            str(value)
            for value in related_ids
        )

        alerts.append(
            {
                "alert_type": "DDI",
                "severity": "BLOCK",
                "message": rule.description,
                "rule_id": str(rule.id),
                "related_medications": related,
                "override_allowed": True,
            }
        )

    # =========================================================
    # 2. DOSE
    # =========================================================

    dose_rules = (
        DURDoseRule.objects
        .filter(
            is_active=True,
            ingredient_id__in=ingredient_ids,
            max_dose__isnull=False,
        )
        .select_related("ingredient")
    )

    dose_by_ingredient = defaultdict(list)

    for rule in dose_rules:
        dose_by_ingredient[
            rule.ingredient_id
        ].append(rule)

    for item in normalized:
        medication_id = item["medication_id"]
        medication = (
            medication_objects[
                medication_id
            ]
        )

        mapping = (
            mappings_by_medication[
                medication_id
            ][0]
        )

        daily_input_mg = (
            item["dose"]
            * Decimal(
                item["frequency_per_day"]
            )
            * TO_MG[item["unit"]]
        )

        for rule in (
            dose_by_ingredient[
                mapping.ingredient_id
            ]
        ):
            if rule.dose_unit not in TO_MG:
                continue

            if not _form_matches(
                medication.dosage_form,
                getattr(
                    rule,
                    "form_name",
                    None,
                ),
            ):
                continue

            max_daily_mg = (
                rule.max_dose
                * TO_MG[rule.dose_unit]
            )

            if daily_input_mg <= max_daily_mg:
                continue

            alerts.append(
                {
                    "alert_type": "DOSE",
                    "severity": "MAJOR",
                    "message": rule.description,
                    "rule_id": str(rule.id),
                    "related_medications": [
                        str(medication_id)
                    ],
                    "override_allowed": True,
                    "observed_daily_dose_mg": (
                        str(daily_input_mg)
                    ),
                    "max_daily_dose_mg": (
                        str(max_daily_mg)
                    ),
                }
            )

    # =========================================================
    # 3. DUPLICATE
    # =========================================================

    duplicate_rules = list(
        DURDuplicateRule.objects
        .filter(
            is_active=True,
            ingredient_id__in=
                relationship_ingredient_ids,
        )
    )

    duplicate_groups = defaultdict(
        lambda: {
            "medications": set(),
            "rules": [],
        }
    )

    for rule in duplicate_rules:
        group = duplicate_groups[
            rule.therapeutic_class_code
        ]

        group["medications"].update(
            relationship_ingredient_to_medications[
                rule.ingredient_id
            ]
        )

        group["rules"].append(rule)

    for class_code, group in (
        duplicate_groups.items()
    ):
        if len(group["medications"]) < 2:
            continue

        # 기존 복용약끼리의 중복만 존재하면
        # 신규 처방 경고로 반환하지 않는다.
        if not (
            group["medications"]
            & medication_ids
        ):
            continue

        rule = group["rules"][0]

        alerts.append(
            {
                "alert_type": "DUPLICATE",
                "severity": "MAJOR",
                "message": (
                    rule.description
                    or (
                        "Therapeutic class "
                        f"duplication: {class_code}"
                    )
                ),
                "rule_id": str(rule.id),
                "related_medications": sorted(
                    str(value)
                    for value
                    in group["medications"]
                ),
                "override_allowed": True,
            }
        )

    # =========================================================
    # 3-A. EXACT CURRENT MEDICATION DUPLICATE
    # =========================================================

    exact_duplicate_ids = (
        medication_ids
        & current_medication_ids
    )

    for medication_id in sorted(
        exact_duplicate_ids,
        key=str,
    ):
        synthetic_rule_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            (
                "brainon://medication-safety/"
                f"current-duplicate/{medication_id}"
            ),
        )

        alerts.append(
            {
                "alert_type":
                    "DUPLICATE",
                "severity":
                    "MAJOR",
                "message":
                    (
                        "현재 복용 중인 동일 약물이 "
                        "이미 있습니다. 중복 처방 여부를 "
                        "확인하세요."
                    ),
                "rule_id":
                    str(synthetic_rule_id),
                "related_medications": [
                    str(medication_id)
                ],
                "override_allowed":
                    True,
            }
        )

    # =========================================================
    # Patient dependent rules
    # =========================================================

    age = _patient_age(patient)

    # =========================================================
    # 4. AGE
    # =========================================================

    if age is not None:
        for rule in (
            DURAgeRule.objects
            .filter(
                is_active=True,
                ingredient_id__in=ingredient_ids,
            )
        ):
            if not _age_rule_matches(
                rule,
                age,
            ):
                continue

            alerts.append(
                {
                    "alert_type": "AGE",
                    "severity": "BLOCK",
                    "message": rule.description,
                    "rule_id": str(rule.id),
                    "related_medications": sorted(
                        str(value)
                        for value
                        in ingredient_to_medications[
                            rule.ingredient_id
                        ]
                    ),
                    "override_allowed": True,
                }
            )

    # =========================================================
    # 5. ELDERLY
    # =========================================================

    if age is not None:
        for rule in (
            DURElderlyRule.objects
            .filter(
                is_active=True,
                ingredient_id__in=ingredient_ids,
            )
        ):
            if age < rule.age_threshold:
                continue

            alerts.append(
                {
                    "alert_type": "ELDERLY",
                    "severity": "WARNING",
                    "message": rule.description,
                    "rule_id": str(rule.id),
                    "related_medications": sorted(
                        str(value)
                        for value
                        in ingredient_to_medications[
                            rule.ingredient_id
                        ]
                    ),
                    "override_allowed": False,
                }
            )

    # =========================================================
    # 6. PREGNANCY
    # =========================================================

    pregnancy_status = (
        getattr(
            patient,
            "pregnancy_status",
            None,
        )
        if patient is not None
        else None
    )

    if (
        str(pregnancy_status or "")
        .strip()
        .upper()
        == "PREGNANT"
    ):
        for rule in (
            DURPregnancyRule.objects
            .filter(
                is_active=True,
                ingredient_id__in=ingredient_ids,
            )
        ):
            alerts.append(
                {
                    "alert_type": "PREGNANCY",
                    "severity": "BLOCK",
                    "message": rule.description,
                    "rule_id": str(rule.id),
                    "related_medications": sorted(
                        str(value)
                        for value
                        in ingredient_to_medications[
                            rule.ingredient_id
                        ]
                    ),
                    "override_allowed": True,
                }
            )

    # =========================================================
    # 7. DURATION
    # =========================================================

    duration_rules = (
        DURDurationRule.objects
        .filter(
            is_active=True,
            ingredient_id__in=ingredient_ids,
            max_duration_days__isnull=False,
        )
        .select_related(
            "ingredient"
        )
    )

    duration_by_ingredient = defaultdict(
        list
    )

    for rule in duration_rules:
        duration_by_ingredient[
            rule.ingredient_id
        ].append(rule)

    for item in normalized:
        if item["duration_days"] is None:
            continue

        medication_id = (
            item["medication_id"]
        )

        medication = (
            medication_objects[
                medication_id
            ]
        )

        mapping = (
            mappings_by_medication[
                medication_id
            ][0]
        )

        for rule in (
            duration_by_ingredient[
                mapping.ingredient_id
            ]
        ):
            if not _form_matches(
                medication.dosage_form,
                rule.form_name,
            ):
                continue

            if (
                item["duration_days"]
                <= rule.max_duration_days
            ):
                continue

            alerts.append(
                {
                    "alert_type": "DURATION",
                    "severity": "MAJOR",
                    "message": rule.description,
                    "rule_id": str(rule.id),
                    "related_medications": [
                        str(medication_id)
                    ],
                    "override_allowed": True,
                    "observed_duration_days": (
                        item["duration_days"]
                    ),
                    "max_duration_days": (
                        rule.max_duration_days
                    ),
                }
            )

    # =========================================================
    # 8. ALLERGY
    # =========================================================

    if patient is not None:
        allergies = list(
            PatientAllergy.objects
            .filter(
                patient=patient,
                status="ACTIVE",
            )
        )

        for allergy in allergies:
            matched_ingredient_ids = set()

            if (
                allergy.ingredient_id
                in ingredient_ids
            ):
                matched_ingredient_ids.add(
                    allergy.ingredient_id
                )

            substance = _normalized_text(
                allergy.substance
            )

            if substance:
                for (
                    ingredient_id,
                    ingredient,
                ) in ingredient_objects.items():
                    names = {
                        _normalized_text(
                            ingredient.name_ko
                        ),
                        _normalized_text(
                            ingredient.name_en
                        ),
                    }

                    names.discard("")

                    if substance in names:
                        matched_ingredient_ids.add(
                            ingredient_id
                        )

            for ingredient_id in (
                matched_ingredient_ids
            ):
                alerts.append(
                    {
                        "alert_type": "ALLERGY",
                        "severity": "BLOCK",
                        "message": (
                            "Patient allergy: "
                            + (
                                allergy.substance
                                or ingredient_objects[
                                    ingredient_id
                                ].name_ko
                            )
                            + (
                                (
                                    f" / reaction: "
                                    f"{allergy.reaction}"
                                )
                                if allergy.reaction
                                else ""
                            )
                        ),
                        "rule_id": str(
                            allergy.id
                        ),
                        "related_medications": (
                            sorted(
                                str(value)
                                for value
                                in ingredient_to_medications[
                                    ingredient_id
                                ]
                            )
                        ),
                        "override_allowed": True,
                    }
                )

    return {
        "safe": not bool(alerts),
        "alerts": alerts,
        "context": {
            "pregnancy_status": (
                pregnancy_status
            ),
            "patient_age": age,
            "checked_at": (
                timezone.now().isoformat()
            ),
            "implemented_rule_types": [
                "DDI",
                "DOSE",
                "DUPLICATE",
                "AGE",
                "ELDERLY",
                "PREGNANCY",
                "DURATION",
                "ALLERGY",
            ],
        },
    }
