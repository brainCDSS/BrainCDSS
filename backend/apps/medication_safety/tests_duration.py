from django.test import TestCase
from django.utils import timezone

from apps.medications.models import Medication

from apps.medication_safety.models import (
    DrugIngredient,
    MedicationIngredient,
    DURDurationRule,
)

from apps.medication_safety.services.dur_activation import (
    apply_dur_activation_policy,
)

from apps.medication_safety.services.dur_rules import (
    parse_max_duration_days,
)

from apps.medication_safety.services.medication_safety import (
    check_medication_safety,
)


class DURDurationRuntimeTests(TestCase):

    def setUp(self):
        self.ingredient = (
            DrugIngredient.objects.create(
                dur_ingredient_code=(
                    "TEST-DURATION-INGR"
                ),
                name_ko="테스트성분",
                name_en="Test Ingredient",
                is_active=True,
            )
        )

        now = timezone.now()

        self.medication = (
            Medication.objects.create(
                medication_code=(
                    "TEST-DURATION-MED"
                ),
                medication_name=(
                    "테스트 투여기간 약품"
                ),
                dosage_form="정제",
                strength=None,
                manufacturer="BrainOn",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        MedicationIngredient.objects.create(
            medication=self.medication,
            ingredient=self.ingredient,
            amount=None,
            unit=None,
            is_active=True,
        )

        self.rule = (
            DURDurationRule.objects.create(
                dur_seq="TEST-DURATION-001",
                ingredient=self.ingredient,
                max_duration_days=21,
                max_duration_raw="21일",
                form_name="정제",
                description=(
                    "테스트 투여기간주의"
                ),
                is_active=True,
            )
        )

    def _alerts(self, duration_days):
        result = check_medication_safety(
            medications=[
                {
                    "medication_id": (
                        self.medication.id
                    ),
                    "dose": "1",
                    "unit": "mg",
                    "frequency_per_day": 1,
                    "duration_days": (
                        duration_days
                    ),
                    "route": "PO",
                }
            ],
            patient=None,
        )

        return [
            alert
            for alert in result["alerts"]
            if alert["alert_type"]
            == "DURATION"
        ]

    def test_duration_parser_exact_days_only(self):
        self.assertEqual(
            parse_max_duration_days(
                "21일"
            ),
            21,
        )

        self.assertIsNone(
            parse_max_duration_days(
                (
                    "무배란증:12일, "
                    "난포과자극유도:20일"
                )
            )
        )

    def test_duration_limit_and_exceed(self):
        self.assertEqual(
            self._alerts(21),
            [],
        )

        alerts = self._alerts(22)

        self.assertEqual(
            len(alerts),
            1,
        )

        alert = alerts[0]

        self.assertEqual(
            alert["severity"],
            "MAJOR",
        )

        self.assertTrue(
            alert["override_allowed"]
        )

        self.assertEqual(
            alert["observed_duration_days"],
            22,
        )

        self.assertEqual(
            alert["max_duration_days"],
            21,
        )

    def test_activation_keeps_unparsed_inactive(self):
        self.rule.is_active = False
        self.rule.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        unparsed = (
            DURDurationRule.objects.create(
                dur_seq="TEST-DURATION-002",
                ingredient=self.ingredient,
                max_duration_days=None,
                max_duration_raw=(
                    "조건A:12일, 조건B:20일"
                ),
                form_name="정제",
                description=(
                    "조건별 투여기간"
                ),
                is_active=True,
            )
        )

        result = (
            apply_dur_activation_policy()
        )

        self.rule.refresh_from_db()
        unparsed.refresh_from_db()

        self.assertTrue(
            self.rule.is_active
        )

        self.assertFalse(
            unparsed.is_active
        )

        self.assertEqual(
            result[
                "DURATION"
            ]["active"],
            1,
        )

        self.assertEqual(
            result[
                "DURATION"
            ]["inactive"],
            1,
        )
