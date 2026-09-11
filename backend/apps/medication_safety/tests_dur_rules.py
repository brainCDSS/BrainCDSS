from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.medication_safety.models import DrugIngredient, DURDoseRule, DURInteractionRule
from apps.medication_safety.services.dur_rules import (
    DURSyncError, make_interaction_key, parse_max_quantity, upsert_dur_rules,
)


def sample_pages():
    # Public ingredient reference data; no patient data or credentials.
    return [
        {"kind": "INTERACTION", "items": [{
            "TYPE_NAME": "병용금기", "MIX_TYPE": "단일",
            "INGR_CODE": "D000762", "INGR_ENG_NAME": "Itraconazole",
            "INGR_KOR_NAME": "이트라코나졸", "MIX": "",
            "ORI": "[M083733]이트라코나졸제피과립", "CLASS": "[06290]기타의 화학요법제",
            "MIXTURE_MIX_TYPE": "단일", "MIXTURE_INGR_CODE": "D000027",
            "MIXTURE_INGR_ENG_NAME": "Simvastatin", "MIXTURE_INGR_KOR_NAME": "심바스타틴",
            "MIXTURE_MIX": "", "MIXTURE_ORI": "[M089710]심바스타틴",
            "MIXTURE_CLASS": "[02180]동맥경화용제", "NOTIFICATION_DATE": "20090303",
            "PROHBT_CONTENT": "횡문근융해증", "REMARK": None, "DEL_YN": "정상",
        }]},
        {"kind": "DOSE", "items": [{
            "DUR_SEQ": "636", "TYPE_NAME": "용량주의", "MIX_TYPE": "단일",
            "INGR_CODE": "D000592", "INGR_ENG_NAME": "Triazolam", "INGR_NAME": "트리아졸람",
            "MIX_INGR": "", "ORI_INGR": "[I005603]트리아졸람/[M088380]트리아졸람",
            "CLASS_NAME": "[01120]최면진정제", "FORM_NAME": "정제", "MAX_QTY": "0.25밀리그램",
            "NOTIFICATION_DATE": "20130703", "PROHBT_CONTENT": None, "REMARK": None,
            "DEL_YN": "정상",
        }]},
    ]


class DURRuleImportTests(TestCase):
    def test_reimport_preserves_ids_and_timestamps(self):
        pages = sample_pages()
        first = upsert_dur_rules(pages)
        stamps = (DURInteractionRule.objects.get().updated_at, DURDoseRule.objects.get().updated_at)
        second = upsert_dur_rules(pages)
        self.assertEqual(first["records"], second["records"])
        self.assertEqual(DrugIngredient.objects.count(), 3)
        for kind in ("INTERACTION", "DOSE"):
            self.assertEqual(second["rules"][kind], {"created": 0, "updated": 0, "unchanged": 1})
        self.assertEqual(stamps, (DURInteractionRule.objects.get().updated_at, DURDoseRule.objects.get().updated_at))

    def test_key_is_symmetric_when_sides_are_swapped(self):
        row = sample_pages()[0]["items"][0]
        swapped = deepcopy(row)
        for a, b in (
            ("INGR_CODE", "MIXTURE_INGR_CODE"), ("MIX_TYPE", "MIXTURE_MIX_TYPE"),
            ("INGR_KOR_NAME", "MIXTURE_INGR_KOR_NAME"), ("INGR_ENG_NAME", "MIXTURE_INGR_ENG_NAME"),
            ("MIX", "MIXTURE_MIX"), ("ORI", "MIXTURE_ORI"), ("CLASS", "MIXTURE_CLASS"),
        ):
            swapped[a], swapped[b] = row[b], row[a]
        self.assertEqual(make_interaction_key(row), make_interaction_key(swapped))
        self.assertLessEqual(len(make_interaction_key(row)), 100)
        self.assertTrue(make_interaction_key(row).startswith("MFDS_DDI_V1_"))

    def test_same_pair_with_different_conditions_keeps_both_rules(self):
        pages = sample_pages()
        another = deepcopy(pages[0]["items"][0])
        another["REMARK"] = "별도 조건 확인용 테스트"
        pages[0]["items"].append(another)
        result = upsert_dur_rules(pages)
        self.assertEqual(result["rules"]["INTERACTION"]["created"], 2)
        self.assertEqual(DURInteractionRule.objects.count(), 2)

    def test_dose_preserves_form_raw_source_and_unknown_period(self):
        pages = sample_pages()
        upsert_dur_rules(pages)
        rule = DURDoseRule.objects.get(dur_seq="636")
        self.assertEqual(rule.form_name, "정제")
        self.assertEqual(rule.max_dose, Decimal("0.25"))
        self.assertEqual(rule.dose_unit, "mg")
        self.assertIsNone(rule.period)
        self.assertIsNone(rule.source_updated_at)
        self.assertEqual(rule.source_payload, pages[1]["items"][0])
        self.assertFalse(rule.is_active)
        self.assertFalse(DURInteractionRule.objects.get().is_active)

    def test_ambiguous_quantity_is_preserved_without_inventing_a_number(self):
        pages = sample_pages()
        pages[1]["items"][0]["MAX_QTY"] = "조건에 따라 0.25~0.5밀리그램"
        upsert_dur_rules(pages)
        rule = DURDoseRule.objects.get()
        self.assertIsNone(rule.max_dose)
        self.assertIsNone(rule.dose_unit)
        self.assertEqual(rule.source_payload["MAX_QTY"], pages[1]["items"][0]["MAX_QTY"])
        self.assertFalse(rule.is_active)

    def test_numeric_limits_are_not_rounded(self):
        for value in ("0.00001mg", "0mg", "-1mg", "10000000000mg", "1mg/day"):
            with self.subTest(value=value):
                self.assertEqual(parse_max_quantity(value), (None, None))

    def test_invalid_source_aborts_before_writing(self):
        for mutation in ({"DUR_SEQ": ""}, {"FORM_NAME": ""}, {"NEW_CONDITION": "x"}, {"DEL_YN": "삭제"}):
            with self.subTest(mutation=mutation):
                pages = sample_pages()
                pages[1]["items"][0].update(mutation)
                with self.assertRaises(DURSyncError):
                    upsert_dur_rules(pages)
                self.assertEqual(DrugIngredient.objects.count(), 0)
                self.assertEqual(DURInteractionRule.objects.count(), 0)

    def test_database_failure_rolls_back_ingredients_and_rules(self):
        from apps.medication_safety.services import dur_rules
        original = dur_rules._save_rule

        def fail_second(model, key, values):
            if model is DURInteractionRule:
                raise RuntimeError("simulated storage failure")
            return original(model, key, values)

        with patch.object(dur_rules, "_save_rule", side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                upsert_dur_rules(sample_pages())
        self.assertEqual(DrugIngredient.objects.count(), 0)
        self.assertEqual(DURDoseRule.objects.count(), 0)
        self.assertEqual(DURInteractionRule.objects.count(), 0)

    def test_dose_update_preserves_id(self):
        pages = sample_pages()
        upsert_dur_rules(pages)
        original_id = DURDoseRule.objects.get().pk
        pages[1]["items"][0]["MAX_QTY"] = "0.5밀리그램"
        result = upsert_dur_rules(pages)
        self.assertEqual(result["rules"]["DOSE"]["updated"], 1)
        self.assertEqual(DURDoseRule.objects.get().pk, original_id)

    def test_same_dose_sequence_cannot_overwrite_another_form(self):
        pages = sample_pages()
        upsert_dur_rules(pages)
        pages[1]["items"][0]["FORM_NAME"] = "주사제"
        with self.assertRaisesMessage(DURSyncError, "DUR_DOSE_SEQ_IDENTITY_CONFLICT"):
            upsert_dur_rules(pages)
        self.assertEqual(DURDoseRule.objects.get().form_name, "정제")

    def test_active_rule_change_requires_review(self):
        pages = sample_pages()
        upsert_dur_rules(pages)
        DURDoseRule.objects.update(is_active=True)
        pages[1]["items"][0]["MAX_QTY"] = "0.5밀리그램"
        with self.assertRaisesMessage(DURSyncError, "DUR_ACTIVE_RULE_UPDATE_REQUIRES_REVIEW"):
            upsert_dur_rules(pages)
        self.assertEqual(DURDoseRule.objects.get().max_dose, Decimal("0.25"))

    def test_unseen_rules_are_not_deactivated_by_partial_import(self):
        pages = sample_pages()
        upsert_dur_rules(pages)
        DURInteractionRule.objects.update(is_active=True)
        upsert_dur_rules([pages[1]])
        self.assertTrue(DURInteractionRule.objects.get().is_active)
