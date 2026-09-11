from rest_framework import serializers


class MedicationSafetyItemSerializer(
    serializers.Serializer
):
    medication_id = serializers.UUIDField()

    dose = serializers.DecimalField(
        max_digits=14,
        decimal_places=4,
    )

    unit = serializers.CharField(
        max_length=30,
    )

    frequency_per_day = (
        serializers.IntegerField(
            min_value=1,
        )
    )

    duration_days = serializers.IntegerField(
        min_value=1,
    )

    route = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class MedicationSafetyRequestSerializer(
    serializers.Serializer
):
    patient_id = serializers.UUIDField()

    medications = (
        MedicationSafetyItemSerializer(
            many=True,
            allow_empty=False,
        )
    )

    draft_prescription_id = (
        serializers.UUIDField(
            required=False,
            allow_null=True,
        )
    )
