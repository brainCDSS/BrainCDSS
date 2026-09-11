import json
from collections import Counter
from math import ceil

from django.core.management.base import BaseCommand, CommandError

from apps.medication_safety.services.dur_rules import (
    SUPPORTED_RULE_KINDS,
    _prepare_rule,
    upsert_dur_rules,
)
from apps.medication_safety.services.dur_sync import (
    DURSyncError,
    extract_ingredients,
    fetch_dur_page,
)


NORMAL = "\uc815\uc0c1"
SINGLE = "\ub2e8\uc77c"

EXPECTED_SKIPPABLE_VALIDATION_ERRORS = {
    "INTERACTION": {
        "DUR_FIELD_REQUIRED:PROHBT_CONTENT",
    },
    "DOSE": {
        "DUR_FIELD_REQUIRED:MAX_QTY",
    },
    "DUPLICATE": set(),
    "AGE": set(),
    "ELDERLY": set(),
    "PREGNANCY": set(),
    "DURATION": set(),
}


class Command(BaseCommand):
    help = (
        "Fetch reviewed MFDS DUR data and stage supported "
        "single-ingredient rules in the local database. "
        "Supported DB-backed kinds: INTERACTION, DOSE, "
        "DUPLICATE, AGE, ELDERLY, PREGNANCY, DURATION."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and validate all source rows without database writes.",
        )
        parser.add_argument(
            "--kind",
            choices=(
                "ALL",
                "BOTH",
                *SUPPORTED_RULE_KINDS,
            ),
            default="ALL",
            help=(
                "DUR rule type to synchronize. "
                "ALL synchronizes all seven DB-backed kinds; "
                "BOTH is retained for legacy "
                "INTERACTION+DOSE behavior."
            ),
        )
        parser.add_argument(
            "--kinds",
            nargs="+",
            choices=SUPPORTED_RULE_KINDS,
            required=False,
            help=(
                "Synchronize an explicit subset of DB-backed "
                "DUR rule types."
            ),
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=100,
            help="MFDS rows per page (1-100). Default: 100.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        selected_kind = options["kind"]
        selected_kinds = options["kinds"]
        page_size = options["page_size"]

        if not 1 <= page_size <= 100:
            raise CommandError("DUR_PAGE_SIZE_INVALID")

        if selected_kinds:
            kinds = tuple(
                dict.fromkeys(
                    selected_kinds
                )
            )
        elif selected_kind == "ALL":
            kinds = tuple(
                SUPPORTED_RULE_KINDS
            )
        elif selected_kind == "BOTH":
            kinds = (
                "INTERACTION",
                "DOSE",
            )
        else:
            kinds = (
                selected_kind,
            )

        eligible_pages = []
        summaries = {}

        try:
            for kind in kinds:
                summary, pages = self._collect_kind(
                    kind=kind,
                    page_size=page_size,
                )

                summaries[kind] = summary
                eligible_pages.extend(pages)

            # Validate ingredient identities across all fetched rule types
            # before allowing any database write.
            ingredients = extract_ingredients(eligible_pages)

        except DURSyncError as exc:
            raise CommandError(str(exc)) from None

        preflight = {
            "dry_run": dry_run,
            "kinds": list(kinds),
            "ingredient_count": len(ingredients),
            "summary": summaries,
        }

        self.stdout.write(
            "DUR_SYNC_PREFLIGHT: "
            + json.dumps(
                preflight,
                ensure_ascii=True,
                sort_keys=True,
            )
        )

        if dry_run:
            self.stdout.write("DUR_SYNC_DRY_RUN_OK")
            self.stdout.write("DB_WRITE: NO")
            return

        try:
            result = upsert_dur_rules(eligible_pages)
        except DURSyncError as exc:
            raise CommandError(str(exc)) from None

        compact_result = {
            "ingredients": result["ingredients"],
            "rules": result["rules"],
            "record_count": len(result["records"]),
        }

        self.stdout.write(
            "DUR_SYNC_SAVE: "
            + json.dumps(
                compact_result,
                ensure_ascii=True,
                sort_keys=True,
            )
        )

        self.stdout.write("DUR_SYNC_DB_WRITE_OK")
        self.stdout.write("DUR_RULES_STAGED_INACTIVE")

    def _collect_kind(self, *, kind, page_size):
        first = fetch_dur_page(
            kind,
            page=1,
            page_size=page_size,
        )

        total_count = first["total_count"]
        total_pages = max(
            1,
            ceil(total_count / page_size),
        )

        fetched_count = 0
        eligible_count = 0

        skipped = Counter()
        validation_errors = Counter()

        prepared = {}
        duplicate_same = 0

        pages = []

        for page_no in range(1, total_pages + 1):
            page = (
                first
                if page_no == 1
                else fetch_dur_page(
                    kind,
                    page=page_no,
                    page_size=page_size,
                )
            )

            if page["total_count"] != total_count:
                raise DURSyncError(
                    "DUR_TOTAL_COUNT_CHANGED_DURING_SYNC"
                )

            fetched_count += len(page["items"])
            eligible_rows = []

            for row in page["items"]:
                del_yn = str(
                    row.get("DEL_YN") or ""
                )

                mix_type = str(
                    row.get("MIX_TYPE") or ""
                )

                if del_yn != NORMAL:
                    skipped[
                        "SOURCE_DELETED_OR_INACTIVE"
                    ] += 1
                    continue

                if mix_type != SINGLE:
                    skipped[
                        "PRIMARY_COMPOSITE"
                    ] += 1
                    continue

                if (
                    kind == "INTERACTION"
                    and str(
                        row.get(
                            "MIXTURE_MIX_TYPE"
                        ) or ""
                    ) != SINGLE
                ):
                    skipped[
                        "SECONDARY_COMPOSITE"
                    ] += 1
                    continue

                try:
                    model, key, values = _prepare_rule(
                        kind,
                        row,
                    )

                except DURSyncError as exc:
                    code = str(exc)

                    if (
                        code
                        in EXPECTED_SKIPPABLE_VALIDATION_ERRORS[
                            kind
                        ]
                    ):
                        validation_errors[code] += 1
                        continue

                    # Unexpected source/schema changes must stop
                    # the sync instead of being silently ignored.
                    raise DURSyncError(
                        f"DUR_UNEXPECTED_SOURCE_RECORD:"
                        f"{kind}:PAGE={page_no}:{code}"
                    ) from None

                identity = (
                    kind,
                    key,
                )

                if identity in prepared:
                    if prepared[identity] != values:
                        raise DURSyncError(
                            "DUR_DUPLICATE_SOURCE_KEY_CONFLICT"
                        )

                    duplicate_same += 1

                else:
                    prepared[identity] = values

                eligible_count += 1
                eligible_rows.append(row)

            if eligible_rows:
                pages.append(
                    {
                        "kind": kind,
                        "total_count": total_count,
                        "items": eligible_rows,
                    }
                )

            self.stdout.write(
                f"DUR_FETCH "
                f"kind={kind} "
                f"page={page_no}/{total_pages} "
                f"rows={len(page['items'])}"
            )

        if fetched_count != total_count:
            raise DURSyncError(
                "DUR_FETCH_COUNT_MISMATCH"
            )

        summary = {
            "source_total": total_count,
            "fetched": fetched_count,
            "eligible_rows": eligible_count,
            "unique_rule_keys": len(prepared),
            "duplicate_same": duplicate_same,
            "skipped": dict(skipped),
            "validation_errors": dict(
                validation_errors
            ),
        }

        return summary, pages
