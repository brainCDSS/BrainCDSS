"""Request and response schemas for surgical planning."""

from rest_framework import serializers

from apps.surgical_planning.models import SurgicalPlan, SurgicalPlanClip, SurgicalPlanMessage, SurgicalPlanStatus


class SurgicalPlanWriteSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    encounter_id = serializers.UUIDField(required=False, allow_null=True)
    study_id = serializers.UUIDField()
    ai_analysis_id = serializers.UUIDField(required=False, allow_null=True)
    treatment_type = serializers.CharField(required=False, allow_blank=True, max_length=100)
    memo = serializers.CharField(required=False, allow_blank=True)


class SurgicalPlanUpdateSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    treatment_type = serializers.CharField(required=False, allow_blank=True, max_length=100)
    memo = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=(SurgicalPlanStatus.IN_PROGRESS, SurgicalPlanStatus.REVIEW_REQUESTED, SurgicalPlanStatus.CANCELLED),
        required=False,
    )


class SurgicalPlanVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class SurgicalPlanClipSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgicalPlanClip
        fields = ("id", "planning_id", "clip_id", "clip_type", "size", "position_x", "position_y", "position_z", "rotation_x", "rotation_y", "rotation_z", "created_at", "updated_at")
        read_only_fields = ("id", "planning_id", "created_at", "updated_at")


class SurgicalPlanClipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurgicalPlanClip
        fields = ("position_x", "position_y", "position_z", "rotation_x", "rotation_y", "rotation_z")
        extra_kwargs = {
            "position_x": {"required": False},
            "position_y": {"required": False},
            "position_z": {"required": False},
            "rotation_x": {"required": False},
            "rotation_y": {"required": False},
            "rotation_z": {"required": False},
        }


class SurgicalPlanMessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()

    class Meta:
        model = SurgicalPlanMessage
        fields = ("id", "planning_id", "sender", "message", "viewer_state", "created_at")
        read_only_fields = ("id", "planning_id", "sender", "created_at")

    def get_sender(self, obj):
        return {"id": obj.sender_id, "name": obj.sender.name, "role": obj.sender.role.code}


class SurgicalPlanSerializer(serializers.ModelSerializer):
    clips = SurgicalPlanClipSerializer(many=True, read_only=True)

    class Meta:
        model = SurgicalPlan
        fields = ("id", "patient_id", "encounter_id", "study_id", "ai_analysis_id", "status", "version", "treatment_type", "memo", "created_by_id", "finalized_by_id", "created_at", "updated_at", "finalized_at", "clips")


class SurgicalPlanListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = SurgicalPlanSerializer(many=True)


class SurgicalPlanClipListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = SurgicalPlanClipSerializer(many=True)


class SurgicalPlanMessageListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = SurgicalPlanMessageSerializer(many=True)
