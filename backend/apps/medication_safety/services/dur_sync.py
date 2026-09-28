"""DUR ingredient import. Rule import is implemented separately."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

from django.db import transaction

from apps.medication_safety.models import DrugIngredient


OPERATIONS = {
    "INTERACTION": "getUsjntTabooInfoList02",
    "DOSE": "getCpctyAtentInfoList02",
    "DUPLICATE": "getEfcyDplctInfoList02",
    "AGE": "getSpcifyAgrdeTabooInfoList02",
    "ELDERLY": "getOdsnAtentInfoList02",
    "PREGNANCY": "getPwnmTabooInfoList02",
    "DURATION": "getMdctnPdAtentInfoList02",
}


class DURSyncError(ValueError):
    pass


def normalize_items(value, depth=0):
    if depth > 8:
        raise DURSyncError("DUR_ITEM_NESTING_TOO_DEEP")
    if value is None or value == "" or value == {}:
        return []
    if isinstance(value, list):
        rows = []
        for item in value:
            rows.extend(normalize_items(item, depth + 1))
        return rows
    if isinstance(value, dict):
        if set(value) == {"item"}:
            return normalize_items(value["item"], depth + 1)
        if "INGR_CODE" in value:
            return [value]
    raise DURSyncError("DUR_ITEM_SHAPE_INVALID")


def fetch_dur_page(kind, *, page=1, page_size=1):
    if kind not in OPERATIONS:
        raise DURSyncError("DUR_KIND_INVALID")
    if type(page) is not int or page < 1:
        raise DURSyncError("DUR_PAGE_INVALID")
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise DURSyncError("DUR_PAGE_SIZE_INVALID")

    base = os.getenv("DUR_INGREDIENT_API_BASE_URL", "").strip().rstrip("/")
    key = unquote(os.getenv("DUR_INGREDIENT_API_KEY", "").strip())
    parts = urlsplit(base)
    if (
        parts.scheme != "https"
        or parts.netloc != "apis.data.go.kr"
        or parts.path != "/1471000/DURIrdntInfoService03"
        or parts.query
        or parts.fragment
    ):
        raise DURSyncError("DUR_INGREDIENT_API_BASE_URL_INVALID")
    if not key or key.startswith("TODO") or not key.isascii():
        raise DURSyncError("DUR_INGREDIENT_API_KEY_INVALID")

    query = urlencode({
        "serviceKey": key,
        "pageNo": page,
        "numOfRows": page_size,
        "type": "json",
    })
    request = Request(
        base + "/" + OPERATIONS[kind] + "?" + query,
        headers={"User-Agent": "BrainOn-CDSS", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read(2_000_001)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise DURSyncError(f"DUR_HTTP_{status}") from None
    except (URLError, TimeoutError, OSError):
        raise DURSyncError("DUR_NETWORK_ERROR") from None

    if len(raw) > 2_000_000:
        raise DURSyncError("DUR_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        root = payload.get("response", payload)
        header = root["header"]
        body = root["body"]
        if str(header["resultCode"]) != "00":
            raise DURSyncError("DUR_API_RESULT_NOT_SUCCESS")
        total = int(body["totalCount"])
        rows = normalize_items(body.get("items"))
        if total < 0 or len(rows) > page_size:
            raise DURSyncError("DUR_PAGE_CONTENT_INVALID")
        expected = min(page_size, max(0, total - (page - 1) * page_size))
        if len(rows) != expected:
            raise DURSyncError("DUR_PAGE_INCOMPLETE")
    except (KeyError, TypeError, AttributeError, UnicodeError, ValueError) as exc:
        if isinstance(exc, DURSyncError):
            raise
        raise DURSyncError("DUR_RESPONSE_INVALID") from None

    return {"kind": kind, "total_count": total, "items": rows}


def extract_ingredients(pages):
    ingredients = {}
    for page in pages:
        kind = page["kind"]
        if kind not in OPERATIONS:
            raise DURSyncError("DUR_KIND_INVALID")
        for row in page["items"]:
            # This initial import handles active single-ingredient records only.
            if row.get("DEL_YN") != "정상" or row.get("MIX_TYPE") != "단일":
                raise DURSyncError("DUR_RECORD_REQUIRES_REVIEW")
            fields = [("INGR_CODE", "INGR_KOR_NAME" if kind == "INTERACTION"
                       else "INGR_NAME", "INGR_ENG_NAME")]
            if kind == "INTERACTION":
                if row.get("MIXTURE_MIX_TYPE") != "단일":
                    raise DURSyncError("DUR_MIXTURE_REQUIRES_REVIEW")
                fields.append(("MIXTURE_INGR_CODE", "MIXTURE_INGR_KOR_NAME",
                               "MIXTURE_INGR_ENG_NAME"))
            for code_field, ko_field, en_field in fields:
                code = row.get(code_field)
                ko = row.get(ko_field)
                en = row.get(en_field)
                if not isinstance(code, str) or not isinstance(ko, str):
                    raise DURSyncError("DUR_INGREDIENT_FIELDS_INVALID")
                if en is not None and not isinstance(en, str):
                    raise DURSyncError("DUR_INGREDIENT_FIELDS_INVALID")
                code, ko, en = code.strip(), ko.strip(), (en or "").strip() or None
                if not code or not ko or len(code) > 80 or len(ko) > 200 or len(en or "") > 200:
                    raise DURSyncError("DUR_INGREDIENT_FIELDS_INVALID")
                names = {"name_ko": ko, "name_en": en}
                if code in ingredients and ingredients[code] != names:
                    raise DURSyncError("DUR_INGREDIENT_NAME_CONFLICT")
                ingredients[code] = names
    return ingredients


def upsert_ingredients(pages):
    # Validate the whole batch before starting any database writes.
    ingredients = extract_ingredients(pages)
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    with transaction.atomic():
        for code, names in sorted(ingredients.items()):
            obj, created = DrugIngredient.objects.select_for_update().get_or_create(
                dur_ingredient_code=code, defaults=names,
            )
            if created:
                counts["created"] += 1
                continue
            changed = []
            for field, value in names.items():
                if getattr(obj, field) != value:
                    setattr(obj, field, value)
                    changed.append(field)
            if changed:
                obj.save(update_fields=[*changed, "updated_at"])
                counts["updated"] += 1
            else:
                counts["unchanged"] += 1
    return {"ingredients": len(ingredients), **counts}
