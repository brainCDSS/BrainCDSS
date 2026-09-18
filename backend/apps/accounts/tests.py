from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import (
    Permission,
    Role,
    RolePermission,
    User,
)


ADMIN_PERMISSION_CODES = {
    "user.manage",
    "role.manage",
    "audit_log.read",
    "dur.sync",
}


class RBACBaselineMigrationTests(TestCase):
    def test_permission_baseline_exists(self):
        self.assertSetEqual(
            set(
                Permission.objects.filter(
                    code__in=ADMIN_PERMISSION_CODES,
                ).values_list("code", flat=True)
            ),
            ADMIN_PERMISSION_CODES,
        )

    def test_only_system_admin_receives_admin_permissions(self):
        mappings = RolePermission.objects.filter(
            permission__code__in=ADMIN_PERMISSION_CODES,
        )

        self.assertSetEqual(
            set(
                mappings.filter(
                    role__code="SYSTEM_ADMIN",
                ).values_list("permission__code", flat=True)
            ),
            ADMIN_PERMISSION_CODES,
        )
        self.assertFalse(
            mappings.exclude(role__code="SYSTEM_ADMIN").exists()
        )

    def test_seed_is_idempotent_and_preserves_existing_patient_read(self):
        neurologist = Role.objects.get(code="NEUROLOGIST")
        patient_read, _ = Permission.objects.get_or_create(
            code="patient.read",
            defaults={
                "name": "환자 조회",
                "domain": "patients",
                "description": "기존 임상 환자 조회 권한",
            },
        )
        existing_mapping, _ = RolePermission.objects.get_or_create(
            role=neurologist,
            permission=patient_read,
        )

        migration = import_module(
            "apps.accounts.migrations.0003_seed_rbac_master"
        )
        migration.seed_rbac_master(django_apps, None)
        migration.seed_rbac_master(django_apps, None)

        self.assertTrue(
            Permission.objects.filter(code="patient.read").exists()
        )
        self.assertTrue(
            RolePermission.objects.filter(
                pk=existing_mapping.pk,
                role=neurologist,
                permission=patient_read,
            ).exists()
        )
        self.assertEqual(
            RolePermission.objects.filter(
                role__code="SYSTEM_ADMIN",
                permission__code__in=ADMIN_PERMISSION_CODES,
            ).count(),
            len(ADMIN_PERMISSION_CODES),
        )


class AdminAPIPermissionRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            login_id="rbac-admin",
            password="test-password",
            name="RBAC Admin",
            role=Role.objects.get(code="SYSTEM_ADMIN"),
        )
        cls.clinician = User.objects.create_user(
            login_id="rbac-neurologist",
            password="test-password",
            name="RBAC Neurologist",
            role=Role.objects.get(code="NEUROLOGIST"),
        )

    def test_system_admin_can_read_admin_users_and_roles(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)

        self.assertEqual(
            client.get("/api/v1/admin/users?page=1").status_code,
            200,
        )
        self.assertEqual(
            client.get("/api/v1/admin/roles").status_code,
            200,
        )

    def test_non_admin_cannot_read_admin_users_or_roles(self):
        client = APIClient()
        client.force_authenticate(user=self.clinician)

        self.assertEqual(
            client.get("/api/v1/admin/users?page=1").status_code,
            403,
        )
        self.assertEqual(
            client.get("/api/v1/admin/roles").status_code,
            403,
        )
