"""Authentication and RBAC persistence models."""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Now


class RoleCode(models.TextChoices):
    PATIENT = "PATIENT", "환자"
    NURSE = "NURSE", "간호사"
    NEUROLOGIST = "NEUROLOGIST", "신경과"
    NEUROSURGEON = "NEUROSURGEON", "신경외과"
    RADIOLOGY = "RADIOLOGY", "영상의학과"
    SYSTEM_ADMIN = "SYSTEM_ADMIN", "관리자"


class Role(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=40,
        unique=True,
        choices=RoleCode.choices,
    )
    name = models.CharField(max_length=80)
    description = models.TextField(
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.code


class Permission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        max_length=80,
        unique=True,
    )
    name = models.CharField(max_length=100)
    domain = models.CharField(
        max_length=40,
        db_index=True,
    )
    description = models.TextField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        db_column="role_id",
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.PROTECT,
        db_column="permission_id",
        related_name="role_permissions",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=Now(),
    )

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="uq_role_permissions_role_permission",
            ),
        ]

    def __str__(self):
        return f"{self.role.code}:{self.permission.code}"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(
        self,
        login_id,
        password,
        *,
        name,
        role,
        email=None,
        **extra_fields,
    ):
        if not login_id:
            raise ValueError("login_id is required.")
        if not password:
            raise ValueError("password is required.")
        if not name:
            raise ValueError("name is required.")
        if role is None:
            raise ValueError("role is required.")

        user = self.model(
            login_id=login_id.strip(),
            name=name.strip(),
            role=role,
            email=self.normalize_email(email) if email else None,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    login_id = models.CharField(
        max_length=50,
        unique=True,
    )
    name = models.CharField(
        max_length=100,
        db_index=True,
    )
    email = models.EmailField(
        max_length=254,
        unique=True,
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        db_column="role_id",
        related_name="users",
    )
    is_active = models.BooleanField(
        default=True,
        db_default=True,
        db_index=True,
    )
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_default=Now(),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_default=Now(),
    )

    objects = UserManager()

    USERNAME_FIELD = "login_id"

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        return self.login_id
