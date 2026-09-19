from django.db import migrations


def grant_nurse_patient_read(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    nurse_role, _ = Role.objects.get_or_create(
        code="NURSE",
        defaults={
            "name": "간호사",
            "description": "Nursing staff",
            "is_active": True,
        },
    )
    patient_read, _ = Permission.objects.get_or_create(
        code="patient.read",
        defaults={
            "name": "환자 조회",
            "domain": "patient",
            "description": "Read patient lists and patient clinical context.",
        },
    )
    RolePermission.objects.get_or_create(
        role=nurse_role,
        permission=patient_read,
    )


def revoke_nurse_patient_read(apps, schema_editor):
    RolePermission = apps.get_model("accounts", "RolePermission")
    RolePermission.objects.filter(
        role__code="NURSE",
        permission__code="patient.read",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            grant_nurse_patient_read,
            revoke_nurse_patient_read,
        ),
    ]
