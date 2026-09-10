from rest_framework import serializers

from apps.imaging.api.imaging_study_serializers import (
    ImagingSeriesSerializer,
    OptionalQueryBooleanField,
)


class ViewerContextQuerySerializer(
    serializers.Serializer
):
    include_ai_overlay = (
        OptionalQueryBooleanField(
            required=False,
            default=True,
        )
    )


class ViewerSessionRequestSerializer(
    serializers.Serializer
):
    purpose = serializers.ChoiceField(
        choices=(
            "DIAGNOSIS",
            "CONSULTATION",
            "FOLLOW_UP",
        )
    )

    include_ai_overlay = serializers.BooleanField(
        default=True
    )


class ViewerSessionSerializer(
    serializers.Serializer
):
    launch_url = serializers.CharField()
    dicomweb_base_url = serializers.CharField()
    viewer_token = serializers.CharField()
    expires_at = serializers.DateTimeField()
    ai_overlay_available = serializers.BooleanField()

    # Frontend compatibility aliases
    viewer_url = serializers.CharField()
    token = serializers.CharField()


class ViewerStudySerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    study_instance_uid = serializers.CharField()
    accession_number = serializers.CharField()
    study_datetime = serializers.DateTimeField(
        allow_null=True
    )
    status = serializers.CharField()


class ViewerAIResultSerializer(serializers.Serializer):
    is_positive = serializers.BooleanField(
        allow_null=True
    )
    confidence = serializers.FloatField(
        allow_null=True
    )
    lesion_count = serializers.IntegerField(
        allow_null=True
    )
    total_volume_ml = serializers.FloatField(
        allow_null=True
    )
    max_diameter_mm = serializers.FloatField(
        allow_null=True
    )
    severity = serializers.CharField()
    structured_findings = serializers.JSONField()


class ViewerArtifactSerializer(
    serializers.Serializer
):
    artifact_id = serializers.UUIDField()
    artifact_type = serializers.CharField()

    dicom_object_reference_id = (
        serializers.UUIDField()
    )

    sop_instance_uid = serializers.CharField()
    retrieve_url = serializers.CharField(
        allow_null=True
    )


class ViewerAISerializer(serializers.Serializer):
    analysis_id = serializers.UUIDField()
    result = ViewerAIResultSerializer()
    artifacts = ViewerArtifactSerializer(
        many=True
    )


class ViewerReportSerializer(
    serializers.Serializer
):
    report_id = serializers.UUIDField()
    status = serializers.CharField()
    version = serializers.IntegerField()

    findings = serializers.CharField()
    impression = serializers.CharField()
    recommendation = serializers.CharField()

    author_id = serializers.UUIDField()
    author_name = serializers.CharField()

    finalized_at = serializers.DateTimeField(
        allow_null=True
    )

    critical_finding = serializers.BooleanField()
    critical_level = serializers.CharField()


class ViewerContextResponseSerializer(
    serializers.Serializer
):
    study = ViewerStudySerializer()
    viewer_session = ViewerSessionSerializer()
    series = ImagingSeriesSerializer(many=True)

    ai = ViewerAISerializer(
        allow_null=True
    )

    final_report = ViewerReportSerializer(
        allow_null=True
    )
