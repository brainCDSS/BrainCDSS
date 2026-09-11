from rest_framework import serializers

from apps.imaging.api.imaging_study_serializers import (
    OptionalQueryBooleanField,
)


class StudyReportQuerySerializer(serializers.Serializer):
    current_only = OptionalQueryBooleanField(
        required=False,
        default=False,
    )

    status = serializers.ChoiceField(
        choices=(
            "DRAFT",
            "PRELIMINARY",
            "FINAL",
            "AMENDED",
            "CANCELLED",
        ),
        required=False,
    )


class ReportUserSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()


class StudyReportItemSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    study_id = serializers.UUIDField()

    status = serializers.CharField()
    version = serializers.IntegerField()
    is_current = serializers.BooleanField()

    findings = serializers.CharField()
    impression = serializers.CharField()
    recommendation = serializers.CharField()

    structured_findings = serializers.JSONField()

    author = ReportUserSerializer()

    referenced_ai_analysis_id = serializers.UUIDField(
        allow_null=True
    )

    preliminary_at = serializers.DateTimeField(
        allow_null=True
    )

    finalized_by = ReportUserSerializer(
        allow_null=True
    )

    finalized_at = serializers.DateTimeField(
        allow_null=True
    )

    critical_finding = serializers.BooleanField()
    critical_level = serializers.CharField()

    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class StudyReportListSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    count = serializers.IntegerField()
    results = StudyReportItemSerializer(many=True)


class TimelineEventSerializer(serializers.Serializer):
    source = serializers.CharField()
    type = serializers.CharField()
    status = serializers.CharField()

    stage = serializers.CharField(
        allow_null=True,
        allow_blank=True,
    )

    occurred_at = serializers.DateTimeField()

    reason_code = serializers.CharField(
        allow_null=True,
        allow_blank=True,
    )

    reason = serializers.CharField(
        allow_null=True,
        allow_blank=True,
    )

    label = serializers.CharField()


class TimelineOrderSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    encounter_id = serializers.UUIDField()
    patient_id = serializers.UUIDField()

    modality = serializers.CharField()
    procedure_code = serializers.CharField()
    priority = serializers.CharField()
    status = serializers.CharField()

    requested_at = serializers.DateTimeField()
    scheduled_at = serializers.DateTimeField(
        allow_null=True
    )


class TimelineStudySerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    study_instance_uid = serializers.CharField()
    accession_number = serializers.CharField()
    status = serializers.CharField()

    study_datetime = serializers.DateTimeField(
        allow_null=True
    )


class TimelineTransferSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    transfer_type = serializers.CharField()
    target_system = serializers.CharField()
    status = serializers.CharField()
    attempt_count = serializers.IntegerField()
    trace_id = serializers.CharField()

    last_error_code = serializers.CharField(
        allow_null=True
    )


class TimelineAnalysisSerializer(serializers.Serializer):
    analysis_id = serializers.UUIDField()
    analysis_type = serializers.CharField()
    status = serializers.CharField()
    stage = serializers.CharField()
    requested_at = serializers.DateTimeField()


class TimelineReportSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    status = serializers.CharField()
    version = serializers.IntegerField()
    is_current = serializers.BooleanField()

    finalized_at = serializers.DateTimeField(
        allow_null=True
    )


class ImagingOrderTimelineSerializer(serializers.Serializer):
    order = TimelineOrderSerializer()
    current_status = serializers.CharField()

    timeline = TimelineEventSerializer(
        many=True
    )

    study = TimelineStudySerializer(
        allow_null=True
    )

    transfer = TimelineTransferSerializer(
        allow_null=True
    )

    analysis = TimelineAnalysisSerializer(
        allow_null=True
    )

    report = TimelineReportSerializer(
        allow_null=True
    )
