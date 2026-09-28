from rest_framework import serializers


ORDER_STATUSES = (
    "PLACED",
    "SCHEDULED",
    "IN_PROGRESS",
    "HELD",
    "COMPLETED",
    "CANCELLED",
)

ORDER_PRIORITIES = (
    "ROUTINE",
    "URGENT",
    "STAT",
)


class ImagingOrderQuerySerializer(serializers.Serializer):
    encounter_id = serializers.UUIDField(
        required=False
    )
    patient_id = serializers.UUIDField(
        required=False
    )
    status = serializers.ChoiceField(
        choices=ORDER_STATUSES,
        required=False,
    )
    modality = serializers.ChoiceField(
        choices=("CT", "MR", "XA"),
        required=False,
    )
    priority = serializers.ChoiceField(
        choices=ORDER_PRIORITIES,
        required=False,
    )
    date_from = serializers.DateField(
        required=False
    )
    date_to = serializers.DateField(
        required=False
    )
    page = serializers.IntegerField(
        min_value=1,
        default=1,
    )
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=20,
    )

    def validate(self, attrs):
        if (
            attrs.get("date_from")
            and attrs.get("date_to")
            and attrs["date_from"] > attrs["date_to"]
        ):
            raise serializers.ValidationError(
                "date_from must be <= date_to."
            )

        return attrs


class ImagingOrderCreateSerializer(serializers.Serializer):
    encounter_id = serializers.UUIDField()
    patient_id = serializers.UUIDField()

    procedure_code = serializers.CharField(
        max_length=64
    )
    procedure_name = serializers.CharField(
        max_length=255
    )

    modality = serializers.ChoiceField(
        choices=("CT", "MR", "XA")
    )

    priority = serializers.ChoiceField(
        choices=ORDER_PRIORITIES
    )

    reason = serializers.CharField()

    def validate_reason(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "reason is required."
            )

        return value


class ImagingOrderUpdateSerializer(serializers.Serializer):
    priority = serializers.ChoiceField(
        choices=ORDER_PRIORITIES,
        required=False,
    )

    reason = serializers.CharField(
        required=False
    )

    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    def validate_reason(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "reason cannot be empty."
            )

        return value

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "At least one editable field is required."
            )

        return attrs


class ImagingOrderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField()

    def validate_reason(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "reason is required."
            )

        return value


class ImagingOrderUserSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()


class ImagingOrderPatientSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()


class ImagingOrderStudySerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    study_instance_uid = serializers.CharField()
    status = serializers.CharField()


class ImagingOrderHistorySerializer(serializers.Serializer):
    previous_status = serializers.CharField(
        allow_null=True
    )
    status = serializers.CharField()
    occurred_at = serializers.DateTimeField()
    reason = serializers.CharField()


class ImagingOrderSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    encounter_id = serializers.UUIDField()
    patient_id = serializers.UUIDField()

    patient = ImagingOrderPatientSerializer()

    accession_number = serializers.CharField(
        allow_null=True,
        allow_blank=True,
    )

    procedure_code = serializers.CharField()
    procedure_name = serializers.CharField()
    modality = serializers.CharField()
    priority = serializers.CharField()
    status = serializers.CharField()
    reason = serializers.CharField()

    requested_by = ImagingOrderUserSerializer()
    requested_at = serializers.DateTimeField()
    scheduled_at = serializers.DateTimeField(
        allow_null=True
    )

    study = ImagingOrderStudySerializer(
        allow_null=True,
        required=False,
    )

    status_history = ImagingOrderHistorySerializer(
        many=True,
        required=False,
    )


class ImagingOrderListResponseSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField()
    next = serializers.CharField(
        allow_null=True
    )
    previous = serializers.CharField(
        allow_null=True
    )
    results = ImagingOrderSerializer(many=True)


class ImagingOrderCancelResponseSerializer(
    serializers.Serializer
):
    order_id = serializers.UUIDField()
    status = serializers.CharField()
    reason = serializers.CharField()
    cancelled_at = serializers.DateTimeField()
