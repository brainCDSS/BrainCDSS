"""Request and response schemas for surgical planning."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.surgical_planning.models import (
    SurgicalPlan,
    SurgicalPlanClip,
    SurgicalPlanMessage,
    SurgicalPlanStatus,
)


class SurgicalPlanWriteSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    encounter_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    study_id = serializers.UUIDField()
    ai_analysis_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    treatment_type = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    memo = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )


class SurgicalPlanUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    treatment_type = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    memo = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )
    status = serializers.ChoiceField(
        choices=(
            SurgicalPlanStatus.IN_PROGRESS,
            SurgicalPlanStatus.REVIEW_REQUESTED,
            SurgicalPlanStatus.CANCELLED,
        ),
        required=False,
    )


class SurgicalPlanVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class SurgicalPlanClipSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgicalPlanClip
        fields = (
            "id",
            "planning_id",
            "clip_id",
            "clip_type",
            "size",
            "position_x",
            "position_y",
            "position_z",
            "rotation_x",
            "rotation_y",
            "rotation_z",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "planning_id",
            "created_at",
            "updated_at",
        )

    def validate_clip_id(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "clip_id must not be blank."
            )

        return value

    def validate_clip_type(self, value):
        value = value.strip().upper()

        if value not in {"STANDARD", "CURVED"}:
            raise serializers.ValidationError(
                "clip_type must be STANDARD or CURVED."
            )

        return value

    def validate_size(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "size must be greater than 0."
            )

        return value


class SurgicalPlanClipUpdateSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = SurgicalPlanClip
        fields = (
            "position_x",
            "position_y",
            "position_z",
            "rotation_x",
            "rotation_y",
            "rotation_z",
        )
        extra_kwargs = {
            "position_x": {"required": False},
            "position_y": {"required": False},
            "position_z": {"required": False},
            "rotation_x": {"required": False},
            "rotation_y": {"required": False},
            "rotation_z": {"required": False},
        }


class SurgicalPlanMessageSerializer(
    serializers.ModelSerializer
):
    sender = serializers.SerializerMethodField()

    class Meta:
        model = SurgicalPlanMessage
        fields = (
            "id",
            "planning_id",
            "sender",
            "message",
            "viewer_state",
            "created_at",
        )
        read_only_fields = (
            "id",
            "planning_id",
            "sender",
            "created_at",
        )

    def validate_message(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "message must not be blank."
            )

        return value

    def validate_viewer_state(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "viewer_state must be a JSON object."
            )

        return value

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                },
                "name": {
                    "type": "string",
                },
                "role": {
                    "type": "string",
                },
            },
            "required": [
                "id",
                "name",
                "role",
            ],
        }
    )
    def get_sender(self, obj):
        return {
            "id": obj.sender_id,
            "name": obj.sender.name,
            "role": obj.sender.role.code,
        }


class SurgicalPlanSerializer(serializers.ModelSerializer):
    clips = SurgicalPlanClipSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SurgicalPlan
        fields = (
            "id",
            "patient_id",
            "encounter_id",
            "study_id",
            "ai_analysis_id",
            "status",
            "version",
            "treatment_type",
            "memo",
            "created_by_id",
            "finalized_by_id",
            "created_at",
            "updated_at",
            "finalized_at",
            "clips",
        )


class SurgicalPlanListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = SurgicalPlanSerializer(many=True)


class SurgicalPlanClipListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = SurgicalPlanClipSerializer(many=True)


class SurgicalPlanMessageListSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField()
    results = SurgicalPlanMessageSerializer(many=True)
