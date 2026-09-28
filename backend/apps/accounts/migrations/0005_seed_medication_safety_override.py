from django.db import migrations


PERMISSION_CODE = "medication_safety.override"

CLINICAL_OVERRIDE_ROLES = (
    "NEUROLOGIST",
    "NEUROSURGEON",
)


def forwards(apps, schema_editor):
    Role = apps.get_model(
        "accounts",
        "Role",
    )
    Permission = apps.get_model(
        "accounts",
        "Permission",
    )
    RolePermission = apps.get_model(
        "accounts",
        "RolePermission",
    )

    check_permission = (
        Permission.objects
        .filter(
            code="medication_safety.check",
        )
        .first()
    )

    if check_permission is None:
        raise RuntimeError(
            "medication_safety.check permission "
            "must exist before seeding override."
        )

    permission, _ = (
        Permission.objects
        .get_or_create(
            code=PERMISSION_CODE,
            defaults={
                "name":
                    "Medication Safety Override",
                "domain":
                    check_permission.domain,
                "description":
                    (
                        "Allows an authorized prescribing "
                        "doctor to finalize a prescription "
                        "after documenting a reason for an "
                        "override-allowed MAJOR/BLOCK "
                        "Medication Safety alert."
                    ),
            },
        )
    )

    for role_code in CLINICAL_OVERRIDE_ROLES:
        role = (
            Role.objects
            .filter(
                code=role_code,
                is_active=True,
            )
            .first()
        )

        if role is None:
            raise RuntimeError(
                f"Required active role missing: "
                f"{role_code}"
            )

        RolePermission.objects.get_or_create(
            role=role,
            permission=permission,
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0004_expand_rbac_master",
        ),
    ]

    operations = [
        migrations.RunPython(
            forwards,
            migrations.RunPython.noop,
        ),
    ]
