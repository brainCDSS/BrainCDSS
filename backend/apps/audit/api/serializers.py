from __future__ import annotations

from datetime import timedelta

from rest_framework import serializers


class AuditListQuerySerializer(
    serializers.Serializer
):
    actor_user_id = serializers.UUIDField(
        required=False
    )
    actor_login_id = serializers.CharField(
        required=False,
        max_length=50,
    )
    actor_role_code = serializers.CharField(
        required=False,
        max_length=40,
    )
    patient_id = serializers.UUIDField(
        required=False
    )
    resource_type = serializers.CharField(
        required=False,
        max_length=80,
    )
    resource_id = serializers.CharField(
        required=False,
        max_length=128,
    )
    action = serializers.CharField(
        required=False,
        max_length=80,
    )
    outcome = serializers.CharField(
        required=False,
        max_length=16,
    )
    request_id = serializers.UUIDField(
        required=False
    )
    tracking_code = serializers.RegexField(
        regex=r"^ERR-[0-9A-Fa-f]{16}$",
        required=False,
        max_length=20,
    )
    occurred_from = serializers.DateTimeField(
        required=False
    )
    occurred_to = serializers.DateTimeField(
        required=False
    )
    reason = serializers.CharField(
        required=False,
        min_length=5,
        max_length=500,
        trim_whitespace=True,
    )
    page = serializers.IntegerField(
        required=False,
        min_value=1,
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
    )

    def validate(self, attrs):
        start = attrs.get(
            "occurred_from"
        )
        end = attrs.get(
            "occurred_to"
        )

        if (
            (start is None)
            != (end is None)
        ):
            raise serializers.ValidationError(
                {
                    "occurred_range": (
                        "occurred_from and occurred_to "
                        "must be provided together."
                    )
                }
            )

        if start and end:
            if start > end:
                raise serializers.ValidationError(
                    {
                        "occurred_range": (
                            "occurred_from must not "
                            "be after occurred_to."
                        )
                    }
                )

            if end - start > timedelta(days=31):
                raise serializers.ValidationError(
                    {
                        "occurred_range": (
                            "Audit range cannot exceed "
                            "31 days."
                        )
                    }
                )

        return attrs


class AuditDetailQuerySerializer(
    serializers.Serializer
):
    reason = serializers.CharField(
        required=True,
        min_length=5,
        max_length=500,
        trim_whitespace=True,
    )
