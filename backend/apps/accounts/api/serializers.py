from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    login_id = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class PasswordChangeRequestSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_new_password(self, value):
        user = self.context.get("user")

        try:
            validate_password(
                value,
                user=user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                list(exc.messages)
            )

        return value


class UserCreateRequestSerializer(serializers.Serializer):
    login_id = serializers.CharField()
    name = serializers.CharField()

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    role_id = serializers.UUIDField()

    temp_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_email(self, value):
        return value or None

    def validate_temp_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                list(exc.messages)
            )

        return value


class UserUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
    )

    email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    role_id = serializers.UUIDField(
        required=False,
    )

    is_active = serializers.BooleanField(
        required=False,
    )

    def validate_email(self, value):
        return value or None


class RolePermissionUpdateRequestSerializer(
    serializers.Serializer
):
    permission_codes = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
    )

    def validate_permission_codes(self, value):
        # 같은 code 중복 입력 방지
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate permission code."
            )

        return value


class RoleBriefSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class PermissionBriefSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    domain = serializers.CharField()


class UserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    login_id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField(
        allow_null=True,
    )
    role = RoleBriefSerializer()
    is_active = serializers.BooleanField()
    last_login = serializers.DateTimeField(
        allow_null=True,
    )
    created_at = serializers.DateTimeField()


class UserDetailSerializer(UserSummarySerializer):
    permissions = serializers.ListField(
        child=serializers.CharField(),
    )
    updated_at = serializers.DateTimeField()


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

    user = serializers.DictField()


class PasswordChangeResponseSerializer(serializers.Serializer):
    changed = serializers.BooleanField()
    password_changed_at = serializers.DateTimeField()


class RoleWithPermissionsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(
        allow_null=True,
    )
    is_active = serializers.BooleanField()
    permissions = PermissionBriefSerializer(
        many=True,
    )


class RolePermissionResponseSerializer(serializers.Serializer):
    role = serializers.DictField()
    permissions = PermissionBriefSerializer(
        many=True,
    )
    updated_at = serializers.DateTimeField()



class PaginatedUserSummaryResponseSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField()

    next = serializers.URLField(
        allow_null=True,
    )

    previous = serializers.URLField(
        allow_null=True,
    )

    results = UserSummarySerializer(
        many=True,
    )


class RoleListResponseSerializer(
    serializers.Serializer
):
    roles = RoleWithPermissionsSerializer(
        many=True,
    )
