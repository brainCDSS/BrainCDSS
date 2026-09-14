from rest_framework import serializers


class FCMTokenRegisterSerializer(
    serializers.Serializer
):
    device_id = serializers.CharField(
        max_length=120,
        trim_whitespace=True,
    )

    platform = serializers.ChoiceField(
        choices=[
            "ANDROID",
            "IOS",
            "WEB",
        ],
    )

    token = serializers.CharField(
        max_length=4096,
        trim_whitespace=True,
    )

    def validate_device_id(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "device_id is required."
            )

        return value

    def validate_token(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "FCM token is required."
            )

        if any(
            character.isspace()
            for character in value
        ):
            raise serializers.ValidationError(
                "FCM token must not contain whitespace."
            )

        return value
