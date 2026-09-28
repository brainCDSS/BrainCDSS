from rest_framework import serializers


SUPPORTED_DUR_SYNC_TYPES = (
    "INTERACTION",
    "DOSE",
    "DUPLICATE",
    "AGE",
    "ELDERLY",
    "PREGNANCY",
    "DURATION",
)


class DurSyncRequestSerializer(
    serializers.Serializer
):
    sync_types = serializers.ListField(
        child=serializers.ChoiceField(
            choices=SUPPORTED_DUR_SYNC_TYPES,
        ),
        required=False,
        allow_empty=False,
    )

    full_sync = serializers.BooleanField(
        required=False,
        default=False,
    )

    def validate(self, attrs):
        if attrs.get("full_sync"):
            raise serializers.ValidationError(
                {
                    "full_sync": (
                        "Full DUR synchronization is not "
                        "enabled by project policy. Use "
                        "sync_types or the default seven "
                        "supported DB-backed DUR types."
                    )
                }
            )

        sync_types = attrs.get(
            "sync_types",
            list(
                SUPPORTED_DUR_SYNC_TYPES
            ),
        )

        normalized = list(
            dict.fromkeys(
                sync_types
            )
        )

        attrs["sync_types"] = normalized

        return attrs


class DurSyncResponseSerializer(
    serializers.Serializer
):
    task_id = serializers.UUIDField()

    status = serializers.ChoiceField(
        choices=("ACCEPTED",),
    )

    requested_sync_types = (
        serializers.ListField(
            child=serializers.CharField(),
        )
    )

    requested_at = (
        serializers.DateTimeField()
    )
