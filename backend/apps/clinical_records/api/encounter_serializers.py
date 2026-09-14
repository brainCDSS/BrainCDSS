from rest_framework import serializers


class EncounterCreateSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    encounter_type = serializers.ChoiceField(
        choices=("EMERGENCY", "OUTPATIENT"),
    )
    appointment_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class EncounterCreateResponseSerializer(serializers.Serializer):
    encounter_id = serializers.UUIDField()
    encounter_no = serializers.CharField()
    patient_id = serializers.UUIDField()
    appointment_id = serializers.UUIDField(allow_null=True)
    encounter_type = serializers.CharField()
    status = serializers.CharField()
    arrived_at = serializers.DateTimeField()


class EncounterListQuerySerializer(serializers.Serializer):
    patient_id = serializers.UUIDField(required=True)
    status = serializers.ChoiceField(
        choices=("IN_PROGRESS", "REGISTERED"),
        required=False,
    )


class EncounterListResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_id = serializers.UUIDField()
    encounter_no = serializers.CharField()
    encounter_type = serializers.CharField()
    status = serializers.CharField()
    arrived_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
