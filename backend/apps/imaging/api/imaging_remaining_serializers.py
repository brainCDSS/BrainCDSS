from rest_framework import serializers


class ResyncRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(
        min_length=5,
        max_length=500,
    )
    force = serializers.BooleanField(
        default=False
    )


class ResyncResponseSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    status = serializers.CharField()
    series_count = serializers.IntegerField()
    instance_count = serializers.IntegerField()
    last_synced_at = serializers.DateTimeField()


class StableStudyEventSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()

    event_type = serializers.ChoiceField(
        choices=(
            "ORTHANC_STABLE_STUDY",
        )
    )

    orthanc_study_id = serializers.CharField(
        max_length=128
    )

    occurred_at = serializers.DateTimeField()


class StableStudyResponseSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    status = serializers.CharField()
    series_count = serializers.IntegerField()
    instance_count = serializers.IntegerField()
    idempotent = serializers.BooleanField()


class ImagingStatusEventSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            "SCHEDULED",
            "IN_PROGRESS",
            "HELD",
            "COMPLETED",
            "CANCELLED",
        )
    )

    occurred_at = serializers.DateTimeField()
    reason = serializers.CharField()

    accession_number = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=64,
    )

    study_instance_uid = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=64,
    )


class ImagingStatusEventResponseSerializer(
    serializers.Serializer
):
    order_id = serializers.UUIDField()
    previous_status = serializers.CharField()
    status = serializers.CharField()
    occurred_at = serializers.DateTimeField()

    study_id = serializers.UUIDField(
        allow_null=True
    )

    idempotent = serializers.BooleanField()


class ReconciliationQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            "OPEN",
            "IN_REVIEW",
            "RESOLVED",
            "IGNORED",
        ),
        default="OPEN",
    )

    issue_code = serializers.CharField(
        required=False,
        max_length=64,
    )

    study_id = serializers.UUIDField(
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


class ReconciliationCandidateSerializer(
    serializers.Serializer
):
    imaging_order_id = serializers.UUIDField()
    patient_id = serializers.UUIDField()
    patient_no = serializers.CharField()
    patient_name = serializers.CharField()
    accession_number = serializers.CharField(
        allow_null=True
    )


class ReconciliationItemSerializer(
    serializers.Serializer
):
    task_id = serializers.UUIDField()
    study_id = serializers.UUIDField()

    imaging_order_id = serializers.UUIDField(
        allow_null=True
    )

    issue_code = serializers.CharField()
    status = serializers.CharField()
    detected_at = serializers.DateTimeField()

    candidates = (
        ReconciliationCandidateSerializer(
            many=True
        )
    )


class ReconciliationListSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField()
    next = serializers.CharField(
        allow_null=True
    )
    previous = serializers.CharField(
        allow_null=True
    )
    results = ReconciliationItemSerializer(
        many=True
    )


class ReconciliationResolveSerializer(
    serializers.Serializer
):
    action = serializers.ChoiceField(
        choices=(
            "RESOLVE",
            "IGNORE",
        )
    )

    patient_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    imaging_order_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    resolution_note = serializers.CharField()

    def validate(self, attrs):
        note = str(
            attrs.get(
                "resolution_note"
            )
            or ""
        ).strip()

        if not note:
            raise serializers.ValidationError(
                "resolution_note is required."
            )

        attrs["resolution_note"] = note

        if attrs["action"] == "RESOLVE":
            if (
                not attrs.get("patient_id")
                or not attrs.get(
                    "imaging_order_id"
                )
            ):
                raise serializers.ValidationError(
                    (
                        "RESOLVE requires "
                        "patient_id and "
                        "imaging_order_id."
                    )
                )

        return attrs


class ReconciliationResolveResponseSerializer(
    serializers.Serializer
):
    task_id = serializers.UUIDField()
    status = serializers.CharField()

    resolved_patient_id = serializers.UUIDField(
        allow_null=True
    )

    resolved_order_id = serializers.UUIDField(
        allow_null=True
    )

    resolved_by = serializers.UUIDField()
    resolved_at = serializers.DateTimeField()
    study_status = serializers.CharField()


class TransferRetrySerializer(serializers.Serializer):
    reason = serializers.CharField(
        min_length=1,
        max_length=500,
    )


class TransferRetryResponseSerializer(
    serializers.Serializer
):
    job_id = serializers.UUIDField()
    status = serializers.CharField()
    attempt_count = serializers.IntegerField()
    trace_id = serializers.CharField()


class DicomQidoQuerySerializer(serializers.Serializer):
    SeriesInstanceUID = serializers.CharField(
        required=False,
        max_length=64,
    )

    Modality = serializers.ChoiceField(
        choices=("CT", "MR", "XA", "SEG", "SR"),
        required=False,
    )

    offset = serializers.IntegerField(
        min_value=0,
        required=False,
    )

    limit = serializers.IntegerField(
        min_value=1,
        max_value=1000,
        required=False,
    )


class DicomStowSerializer(serializers.Serializer):
    analysis_id = serializers.UUIDField()
    result_id = serializers.UUIDField()

    artifact_type = serializers.ChoiceField(
        choices=(
            "DICOM_SEG",
            "DICOM_SR",
        )
    )

    artifact_uri = serializers.CharField(
        max_length=1024
    )

    sop_instance_uid = serializers.CharField(
        max_length=64
    )

    series_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    target_system = serializers.CharField(
        max_length=64
    )


class DicomStowResponseSerializer(
    serializers.Serializer
):
    transfer_job_id = serializers.UUIDField()
    artifact_id = serializers.UUIDField()
    dicom_object_reference_id = serializers.UUIDField()
    status = serializers.CharField()
