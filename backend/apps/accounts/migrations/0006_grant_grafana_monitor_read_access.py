from django.db import migrations


MONITOR_ROLE = "brainon_monitor"

# Keep this list aligned with the PostgreSQL-backed Grafana dashboard queries.
# CTE aliases such as ai_stats, audit_stats, and events are intentionally absent.
DASHBOARD_TABLES = (
    "accounts_user",
    "ai_aianalysis",
    "audit_auditlog",
    "common_outboxevent",
    "roles",
)


def grant_dashboard_read_access(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    quoted_role = schema_editor.quote_name(MONITOR_ROLE)
    quoted_tables = ", ".join(
        schema_editor.quote_name(table)
        for table in DASHBOARD_TABLES
    )

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s",
            [MONITOR_ROLE],
        )
        if cursor.fetchone() is None:
            return

        cursor.execute(f"GRANT USAGE ON SCHEMA public TO {quoted_role}")
        cursor.execute(
            f"GRANT SELECT ON TABLE {quoted_tables} TO {quoted_role}"
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0005_seed_medication_safety_override",
        ),
    ]

    operations = [
        migrations.RunPython(
            grant_dashboard_read_access,
            migrations.RunPython.noop,
        ),
    ]
