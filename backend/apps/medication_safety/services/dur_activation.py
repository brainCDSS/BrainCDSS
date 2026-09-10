"""Activation policy for locally synchronized DUR rules."""

from django.db import transaction

from apps.medication_safety.models import (
    DURInteractionRule,
    DURDoseRule,
)


SUPPORTED_DOSE_UNITS = (
    "mg",
    "g",
    "mcg",
)


@transaction.atomic
def apply_dur_activation_policy():
    """
    Activate only DUR rules that are safe for runtime evaluation.

    INTERACTION:
      - both ingredients active
      - non-empty description

    DOSE:
      - ingredient active
      - positive parsed max_dose
      - supported normalized unit
      - non-empty description

    Unparseable/incomplete dose rows remain inactive.
    """

    interaction_valid = (
        DURInteractionRule.objects
        .filter(
            ingredient_a__is_active=True,
            ingredient_b__is_active=True,
        )
        .exclude(description="")
    )

    interaction_activated = (
        interaction_valid
        .filter(is_active=False)
        .update(is_active=True)
    )

    interaction_deactivated = (
        DURInteractionRule.objects
        .filter(is_active=True)
        .exclude(
            pk__in=interaction_valid.values("pk")
        )
        .update(is_active=False)
    )

    dose_valid = (
        DURDoseRule.objects
        .filter(
            ingredient__is_active=True,
            max_dose__gt=0,
            dose_unit__in=SUPPORTED_DOSE_UNITS,
        )
        .exclude(description="")
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

    return {
        "INTERACTION": {
            "active": (
                DURInteractionRule.objects
                .filter(is_active=True)
                .count()
            ),
            "inactive": (
                DURInteractionRule.objects
                .filter(is_active=False)
                .count()
            ),
            "activated": interaction_activated,
            "deactivated": interaction_deactivated,
        },
        "DOSE": {
            "active": (
                DURDoseRule.objects
                .filter(is_active=True)
                .count()
            ),
            "inactive": (
                DURDoseRule.objects
                .filter(is_active=False)
                .count()
            ),
            "activated": dose_activated,
            "deactivated": dose_deactivated,
        },
    }
