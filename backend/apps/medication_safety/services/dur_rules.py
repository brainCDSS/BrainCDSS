"""Persist reviewed DUR source shapes without activating clinical rules.

Uses the existing dur_sync.py client and ingredient importer. DDI identifiers
are internal source-version fingerprints, not identifiers issued by MFDS.
"""

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.medication_safety.models import (
    DrugIngredient,
    DURDoseRule,
    DURInteractionRule,
)
from .dur_sync import DURSyncError, extract_ingredients, upsert_ingredients


DDI_FIELDS = {
    "DUR_SEQ", "TYPE_NAME", "MIX_TYPE", "INGR_CODE", "INGR_ENG_NAME",
    "INGR_KOR_NAME", "MIX", "ORI", "CLASS", "MIXTURE_MIX_TYPE",
    "MIXTURE_INGR_CODE", "MIXTURE_INGR_ENG_NAME", "MIXTURE_INGR_KOR_NAME",
    "MIXTURE_MIX", "MIXTURE_ORI", "MIXTURE_CLASS", "NOTIFICATION_DATE",
    "PROHBT_CONTENT", "REMARK", "DEL_YN",
}
DOSE_FIELDS = {
    "DUR_SEQ", "TYPE_NAME", "MIX_TYPE", "INGR_CODE", "INGR_ENG_NAME",
    "INGR_NAME", "MIX_INGR", "ORI_INGR", "CLASS_NAME", "FORM_NAME",
    "MAX_QTY", "NOTIFICATION_DATE", "PROHBT_CONTENT", "REMARK", "DEL_YN",
}


def _text(row, field, *, required=False, limit=None):
    value = row.get(field)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise DURSyncError(f"DUR_FIELD_TYPE_INVALID:{field}")
    value = unicodedata.normalize("NFC", value).strip()
    if required and not value:
        raise DURSyncError(f"DUR_FIELD_REQUIRED:{field}")
    if limit is not None and len(value) > limit:
        raise DURSyncError(f"DUR_FIELD_TOO_LONG:{field}")
    return value


def _validate_row(row, kind):
    allowed = DDI_FIELDS if kind == "INTERACTION" else DOSE_FIELDS
    if not isinstance(row, dict) or not set(row).issubset(allowed):
        raise DURSyncError("DUR_SOURCE_FIELDS_REQUIRE_REVIEW")
    for field in row:
        _text(row, field)
    expected_type = "병용금기" if kind == "INTERACTION" else "용량주의"
    if _text(row, "TYPE_NAME", required=True) != expected_type:
        raise DURSyncError("DUR_SOURCE_TYPE_MISMATCH")
    if _text(row, "DEL_YN") != "정상" or _text(row, "MIX_TYPE") != "단일":
        raise DURSyncError("DUR_SOURCE_STATUS_OR_MIX_REQUIRES_REVIEW")
    _text(row, "INGR_CODE", required=True, limit=80)
    date = _text(row, "NOTIFICATION_DATE")
    if date:
        try:
            if not re.fullmatch(r"[0-9]{8}", date):
                raise ValueError
            datetime.strptime(date, "%Y%m%d")
        except ValueError:
            raise DURSyncError("DUR_NOTIFICATION_DATE_INVALID") from None


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_interaction_key(row):
    """Symmetric DDI source-version key including conditions, not just codes."""
    _validate_row(row, "INTERACTION")
    if _text(row, "MIXTURE_MIX_TYPE") != "단일":
        raise DURSyncError("DUR_MIXTURE_REQUIRES_REVIEW")
    _text(row, "MIXTURE_INGR_CODE", required=True, limit=80)
    _text(row, "PROHBT_CONTENT", required=True)
    sides = []
    for code, mix_type, mix, ori, classification in (
        ("INGR_CODE", "MIX_TYPE", "MIX", "ORI", "CLASS"),
        ("MIXTURE_INGR_CODE", "MIXTURE_MIX_TYPE", "MIXTURE_MIX",
         "MIXTURE_ORI", "MIXTURE_CLASS"),
    ):
        sides.append({
            "code": _text(row, code), "mix_type": _text(row, mix_type),
            "mix": _text(row, mix), "ori": _text(row, ori),
            "classification": _text(row, classification),
        })
    if sides[0]["code"] == sides[1]["code"]:
        raise DURSyncError("DUR_SELF_INTERACTION_REQUIRES_REVIEW")
    identity = {
        "schema": "brainon-mfds-ddi-source-v1",
        "participants": sorted(sides, key=_canonical),
        "notification_date": _text(row, "NOTIFICATION_DATE"),
        "prohibition": _text(row, "PROHBT_CONTENT"),
        "remark": _text(row, "REMARK"),
    }
    digest = hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()
    return "MFDS_DDI_V1_" + digest


def parse_max_quantity(raw):
    """Parse one unambiguous terminal quantity from MFDS MAX_QTY.

    Accepted examples:
    - "100밀리그램"
    - "라미프릴 10밀리그램"
    - "(고령자)멕사졸람 1.5밀리그램"
    - "덱시부프로펜 1,200밀리그램"

    Conservative safety rules:
    - signed, ranged, calculated, or multi-quantity expressions are not parsed
    - other numeric content before the final quantity makes the value ambiguous
    - the quantity must be the final meaningful token
    - source_payload retains the original source text
    """
    if not isinstance(raw, str):
        return None, None

    text = unicodedata.normalize("NFC", raw).strip()
    if not text:
        return None, None

    pattern = re.compile(
        r"(?<![0-9])"
        r"(?P<amount>"
        r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)"
        r"(?:\.[0-9]+)?"
        r")"
        r"\s*"
        r"(?P<unit>"
        r"밀리그램|마이크로그램|그램|mg|mcg|ug|μg|㎎|㎍|g"
        r")",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(text))

    # More than one explicit supported quantity is ambiguous.
    if len(matches) != 1:
        return None, None

    match = matches[0]

    # Nothing meaningful may follow the parsed quantity.
    if text[match.end():].strip():
        return None, None

    prefix = text[:match.start()].strip()

    # Any earlier numeric value means that selecting only the final
    # quantity would require clinical/source interpretation.
    if re.search(r"[0-9]", prefix):
        return None, None

    # Do not turn signed/ranged/comparison/calculated expressions
    # into a positive scalar value.
    if re.search(r"[+\-−–—~～<>≤≥=/]", prefix):
        return None, None

    amount_text = match.group("amount").replace(",", "")
    unit_text = match.group("unit").lower()

    units = {
        "밀리그램": "mg",
        "mg": "mg",
        "㎎": "mg",
        "그램": "g",
        "g": "g",
        "마이크로그램": "mcg",
        "mcg": "mcg",
        "ug": "mcg",
        "μg": "mcg",
        "㎍": "mcg",
    }

    try:
        amount = Decimal(amount_text)

        if not 0 < amount <= Decimal("9999999999.9999"):
            return None, None

        # DB decimal_places=4. Never round source limits.
        if amount != amount.quantize(Decimal("0.0001")):
            return None, None

    except (InvalidOperation, ValueError):
        return None, None

    unit = units.get(unit_text)
    if unit is None:
        return None, None

    return amount, unit

def _prepare_rule(kind, row):
    if kind == "INTERACTION":
        key = make_interaction_key(row)
        codes = sorted((_text(row, "INGR_CODE"), _text(row, "MIXTURE_INGR_CODE")))
        description = _text(row, "PROHBT_CONTENT", required=True)
        remark = _text(row, "REMARK")
        if remark:
            description += "\n비고: " + remark
        return DURInteractionRule, key, {
            "ingredient_a_code": codes[0], "ingredient_b_code": codes[1],
            "description": description, "source": "MFDS_DUR",
            "source_payload": deepcopy(row),
        }
    _validate_row(row, "DOSE")
    key = _text(row, "DUR_SEQ", required=True, limit=100)
    form = _text(row, "FORM_NAME", required=True, limit=200)
    raw_qty = _text(row, "MAX_QTY", required=True)
    quantity, unit = parse_max_quantity(raw_qty)
    description = f"제형: {form}\n최대용량 원문: {raw_qty}"
    for field, label in (("PROHBT_CONTENT", "금기내용"), ("REMARK", "비고")):
        value = _text(row, field)
        if value:
            description += f"\n{label}: {value}"
    return DURDoseRule, key, {
        "ingredient_code": _text(row, "INGR_CODE"),
        "form_name": form, "max_dose": quantity, "dose_unit": unit,
        "period": None, "description": description, "source_payload": deepcopy(row),
    }


def _save_rule(model, key, values):
    obj, created = model.objects.select_for_update().get_or_create(
        dur_seq=key, defaults={**values, "is_active": False},
    )
    if created:
        return obj, "created"
    if model is DURDoseRule and (
        obj.ingredient_id != values["ingredient_id"]
        or (obj.form_name and obj.form_name != values["form_name"])
    ):
        raise DURSyncError("DUR_DOSE_SEQ_IDENTITY_CONFLICT")
    changed = [field for field, value in values.items() if getattr(obj, field) != value]
    if changed and obj.is_active:
        raise DURSyncError("DUR_ACTIVE_RULE_UPDATE_REQUIRES_REVIEW")
    if changed:
        for field in changed:
            setattr(obj, field, values[field])
        obj.save(update_fields=[*changed, "updated_at"])
        return obj, "updated"
    return obj, "unchanged"


def upsert_dur_rules(pages):
    """Atomic additive import. Missing rows never deactivate existing rules.

    New rules remain inactive until MedicationSafety evaluates their conditions.
    No external requests are performed inside the database transaction.
    """
    pages = list(pages)
    extract_ingredients(pages)
    prepared = {}
    for page in pages:
        for row in page["items"]:
            model, key, values = _prepare_rule(page["kind"], row)
            identity = (page["kind"], key)
            if identity in prepared:
                if prepared[identity][1] != values:
                    raise DURSyncError("DUR_DUPLICATE_SOURCE_KEY_CONFLICT")
            else:
                prepared[identity] = (model, values)
    counts = {
        kind: {"created": 0, "updated": 0, "unchanged": 0}
        for kind in ("INTERACTION", "DOSE")
    }
    saved = []
    with transaction.atomic():
        ingredient_counts = upsert_ingredients(pages)
        ingredient_codes = extract_ingredients(pages)
        ingredients = DrugIngredient.objects.in_bulk(
            ingredient_codes, field_name="dur_ingredient_code",
        )
        for (kind, key), (model, prepared_values) in sorted(prepared.items()):
            values = deepcopy(prepared_values)
            fields = ("ingredient_a", "ingredient_b") if kind == "INTERACTION" else ("ingredient",)
            for field in fields:
                code = values.pop(field + "_code")
                values[field + "_id"] = ingredients[code].pk
            obj, outcome = _save_rule(model, key, values)
            counts[kind][outcome] += 1
            saved.append({"kind": kind, "dur_seq": key, "id": str(obj.pk), "is_active": obj.is_active})
    return {"ingredients": ingredient_counts, "rules": counts, "records": saved}
