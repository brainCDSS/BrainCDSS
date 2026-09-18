from django.db import migrations


ROLE_BASELINE = (
    ("PATIENT", "환자"),
    ("NURSE", "간호사"),
    ("NEUROLOGIST", "신경과"),
    ("NEUROSURGEON", "신경외과"),
    ("RADIOLOGY", "영상의학과"),
    ("SYSTEM_ADMIN", "관리자"),
)

PERMISSION_BASELINE = (
    (
        "user.manage",
        "사용자 관리",
        "accounts",
        "관리자 사용자 계정을 조회하고 관리합니다.",
    ),
    (
        "role.manage",
        "역할 및 권한 관리",
        "accounts",
        "역할별 권한 구성을 조회하고 관리합니다.",
    ),
    (
        "audit_log.read",
        "감사 로그 조회",
        "audit",
        "보안 정책에 따라 감사 로그를 조회합니다.",
    ),
    (
        "dur.sync",
        "DUR 기준정보 동기화",
        "medication_safety",
        "의약품 안전성 기준정보 동기화를 요청합니다.",
    ),
)


def seed_rbac_master(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    roles = {}
    for code, name in ROLE_BASELINE:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": name},
        )
        roles[code] = role

    permissions = {}
    for code, name, domain, description in PERMISSION_BASELINE:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "domain": domain,
                "description": description,
            },
        )
        permissions[code] = permission

    system_admin = roles["SYSTEM_ADMIN"]
    for permission in permissions.values():
        RolePermission.objects.get_or_create(
            role=system_admin,
            permission=permission,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_rbac_master,
            migrations.RunPython.noop,
        ),
    ]
