"""Activation policy for synchronized MFDS DUR rules."""

from django.db import transaction
from django.db.models import F, Q

from apps.medication_safety.models import (
    DURAgeRule,
    DURDoseRule,
    DURDuplicateRule,
    DURDurationRule,
    DURElderlyRule,
    DURInteractionRule,
    DURPregnancyRule,
)


SUPPORTED_DOSE_UNITS = {
    "mg",
    "g",
    "mcg",
}


@transaction.atomic
def apply_dur_activation_policy():

    # ========================================================
    # 1. INTERACTION
    # ========================================================

    interaction_valid = (
        DURInteractionRule.objects.all()
    )

    interaction_activated = (
        interaction_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    interaction_deactivated = 0

    # ========================================================
    # 2. DOSE
    # ========================================================

    dose_valid = (
        DURDoseRule.objects
        .filter(
            max_dose__isnull=False,
            max_dose__gt=0,
            dose_unit__in=SUPPORTED_DOSE_UNITS,
        )
    )

    dose_activated = (
        dose_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    dose_deactivated = (
        DURDoseRule.objects
        .filter(is_active=True)
        .exclude(
            pk__in=dose_valid.values("pk")
        )
        .update(is_active=False)
    )

    # ========================================================
    # 3. DUPLICATE
    # ========================================================

    duplicate_valid = (
        DURDuplicateRule.objects
        .exclude(
            therapeutic_class_code=""
        )
    )

    duplicate_activated = (
        duplicate_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    duplicate_deactivated = (
        DURDuplicateRule.objects
        .filter(is_active=True)
        .exclude(
            pk__in=duplicate_valid.values("pk")
        )
        .update(is_active=False)
    )

    # ========================================================
    # 4. AGE
    #
    # 월/주 기준 등 정확한 연령으로 변환되지 않은 source는
    # min_age/max_age 둘 다 NULL이므로 inactive 유지.
    # ========================================================

    age_valid = (
        DURAgeRule.objects
        .filter(
            Q(min_age__isnull=False)
            | Q(max_age__isnull=False)
        )
        .filter(
            Q(min_age__isnull=True)
            | Q(min_age__gte=0)
        )
        .filter(
            Q(max_age__isnull=True)
            | Q(max_age__gte=0)
        )
        .filter(
            Q(min_age__isnull=True)
            | Q(max_age__isnull=True)
            | Q(min_age__lte=F("max_age"))
        )
    )

    age_activated = (
        age_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    age_deactivated = (
        DURAgeRule.objects
        .filter(is_active=True)
        .exclude(
            pk__in=age_valid.values("pk")
        )
        .update(is_active=False)
    )

    # ========================================================
    # 5. ELDERLY
    #
    # 현재 BrainOn 정책:
    # 노인주의 runtime threshold = 65세
    # ========================================================

    elderly_valid = (
        DURElderlyRule.objects
        .filter(
            age_threshold=65
        )
    )

    elderly_activated = (
        elderly_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    elderly_deactivated = (
        DURElderlyRule.objects
        .filter(is_active=True)
        .exclude(
            pk__in=elderly_valid.values("pk")
        )
        .update(is_active=False)
    )

    # ========================================================
    # 6. PREGNANCY
    #
    # Runtime은 patient.pregnancy_status=PREGNANT인 경우에만
    # 해당 Rule을 평가한다.
    # ========================================================

    pregnancy_valid = (
        DURPregnancyRule.objects.all()
    )

    pregnancy_activated = (
        pregnancy_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    pregnancy_deactivated = 0

    # ========================================================
    # 7. DURATION
    #
    # 단일 양의 정수 일수로 확정된 규칙만 활성화.
    # 조건별 복수 기간은 NULL 상태로 inactive 유지.
    # ========================================================

    duration_valid = (
        DURDurationRule.objects
        .filter(
            max_duration_days__isnull=False,
            max_duration_days__gt=0,
        )
    )

    duration_activated = (
        duration_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    duration_deactivated = (
        DURDurationRule.objects
        .filter(is_active=True)
        .exclude(
            pk__in=duration_valid.values("pk")
        )
        .update(is_active=False)
    )

    def summary(
        model,
        activated,
        deactivated,
    ):
        return {
            "activated": activated,
            "deactivated": deactivated,
            "active": (
                model.objects
                .filter(is_active=True)
                .count()
            ),
            "inactive": (
                model.objects
                .filter(is_active=False)
                .count()
            ),
        }

    return {
        "INTERACTION": summary(
            DURInteractionRule,
            interaction_activated,
            interaction_deactivated,
        ),
        "DOSE": summary(
            DURDoseRule,
            dose_activated,
            dose_deactivated,
        ),
        "DUPLICATE": summary(
            DURDuplicateRule,
            duplicate_activated,
            duplicate_deactivated,
        ),
        "AGE": summary(
            DURAgeRule,
            age_activated,
            age_deactivated,
        ),
        "ELDERLY": summary(
            DURElderlyRule,
            elderly_activated,
            elderly_deactivated,
        ),
        "PREGNANCY": summary(
            DURPregnancyRule,
            pregnancy_activated,
            pregnancy_deactivated,
        ),
        "DURATION": summary(
            DURDurationRule,
            duration_activated,
            duration_deactivated,
        ),
    }
