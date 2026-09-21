from rest_framework import serializers
from rest_framework.fields import empty


class OptionalQueryBooleanField(serializers.BooleanField):
    """
    Query parameter에서 key 자체가 없으면
    False가 아니라 '미지정'으로 유지한다.
    """

    def get_value(self, dictionary):
        if self.field_name not in dictionary:
            return empty

        return super().get_value(dictionary)


class ImagingStudyListQuerySerializer(serializers.Serializer):
    patient_id = serializers.UUIDField(required=False)
    accession_number = serializers.CharField(required=False)
    modality = serializers.ChoiceField(
        choices=("CT", "MR", "XA"),
        required=False,
    )
    procedure_code = serializers.CharField(required=False)
    scan_type = serializers.ChoiceField(
        choices=("CTA", "MRA"),
        required=False,
    )
    status = serializers.ChoiceField(
        choices=(
            "RECEIVING",
            "AVAILABLE",
            "INCOMPLETE",
            "UNMATCHED",
            "ERROR",
        ),
        required=False,
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    has_ai_result = OptionalQueryBooleanField(required=False)
    ai_status = serializers.CharField(required=False)
    report_status = serializers.CharField(required=False)
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
        start = attrs.get("date_from")
        end = attrs.get("date_to")

        if start and end and start > end:
            raise serializers.ValidationError(
                "date_from must be on or before date_to."
            )

        return attrs


class ImagingAnalysisSummarySerializer(serializers.Serializer):
    analysis_id = serializers.UUIDField()
    status = serializers.CharField()


class ImagingReportSummarySerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    status = serializers.CharField()


class ImagingPatientSummarySerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField(
        allow_null=True
    )
    estimated_age = serializers.IntegerField(
        allow_null=True
    )
    sex = serializers.CharField(
        allow_null=True
    )


class ImagingStudyListItemSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    accession_number = serializers.CharField()
    study_datetime = serializers.DateTimeField(
        allow_null=True
    )
    modalities = serializers.ListField(
        child=serializers.CharField()
    )
    status = serializers.CharField()
    series_count = serializers.IntegerField()
    instance_count = serializers.IntegerField()

    latest_analysis = ImagingAnalysisSummarySerializer(
        allow_null=True
    )
    current_report = ImagingReportSummarySerializer(
        allow_null=True
    )
    critical_finding = serializers.BooleanField()

    patient = ImagingPatientSummarySerializer(
        allow_null=True
    )
    scan_type = serializers.CharField(
        allow_null=True
    )


class ImagingStudyListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ImagingStudyListItemSerializer(many=True)


class ImagingSeriesSerializer(serializers.Serializer):
    series_id = serializers.UUIDField()
    series_instance_uid = serializers.CharField()
    series_number = serializers.IntegerField(
        allow_null=True
    )
    modality = serializers.CharField()
    series_description = serializers.CharField()

    instance_count = serializers.IntegerField()
    slice_thickness = serializers.FloatField(
        allow_null=True
    )
    is_complete = serializers.BooleanField()
    is_ai_eligible = serializers.BooleanField()
    ai_exclusion_reason = serializers.CharField()


class ImagingStudyDetailSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    study_instance_uid = serializers.CharField()
    accession_number = serializers.CharField()
    study_datetime = serializers.DateTimeField(
        allow_null=True
    )
    status = serializers.CharField()

    patient = ImagingPatientSummarySerializer(
        allow_null=True
    )
    series = ImagingSeriesSerializer(many=True)

    latest_analysis = ImagingAnalysisSummarySerializer(
        allow_null=True
    )
    current_report = ImagingReportSummarySerializer(
        allow_null=True
    )


class ImagingSeriesQuerySerializer(serializers.Serializer):
    modality = serializers.ChoiceField(
        choices=("CT", "MR"),
        required=False,
    )
    ai_eligible = OptionalQueryBooleanField(
        required=False,
    )
    complete = OptionalQueryBooleanField(
        required=False,
    )


class ImagingSeriesResponseSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()
    series = ImagingSeriesSerializer(many=True)

class StudyAIHistoryQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            "QUEUED",
            "PROCESSING",
            "COMPLETED",
            "FAILED",
            "RETRYING",
            "CANCELLED",
        ),
        required=False,
    )
    analysis_type = serializers.CharField(
        required=False,
        max_length=64,
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


class StudyAIModelSerializer(serializers.Serializer):
    code = serializers.CharField()
    version = serializers.CharField()


class StudyAIResultSummarySerializer(serializers.Serializer):
    is_positive = serializers.BooleanField(
        allow_null=True
    )
    total_volume_ml = serializers.FloatField(
        allow_null=True
    )


class StudyAIHistoryItemSerializer(serializers.Serializer):
    analysis_id = serializers.UUIDField()
    analysis_type = serializers.CharField()
    status = serializers.CharField()
    stage = serializers.CharField()

    model = StudyAIModelSerializer()

    attempt_count = serializers.IntegerField()
    requested_at = serializers.DateTimeField()

    result_summary = StudyAIResultSummarySerializer(
        allow_null=True
    )


class StudyAIHistoryResponseSerializer(serializers.Serializer):
    study_id = serializers.UUIDField()

    # Backend/Frontend 공통 Pagination 계약
    count = serializers.IntegerField()
    next = serializers.CharField(
        allow_null=True
    )
    previous = serializers.CharField(
        allow_null=True
    )

    results = StudyAIHistoryItemSerializer(
        many=True
    )



class DerivedDicomObjectSerializer(serializers.Serializer):
    type = serializers.CharField()
    sop_instance_uid = serializers.CharField()


class ImagingSeriesDetailSerializer(serializers.Serializer):
    series_id = serializers.UUIDField()
    study_id = serializers.UUIDField()
    series_instance_uid = serializers.CharField()
    modality = serializers.CharField()

    protocol_name = serializers.CharField()
    series_description = serializers.CharField()

    instance_count = serializers.IntegerField()
    frame_count = serializers.IntegerField()

    rows = serializers.IntegerField(
        allow_null=True
    )
    columns = serializers.IntegerField(
        allow_null=True
    )
    slice_thickness = serializers.FloatField(
        allow_null=True
    )

    is_complete = serializers.BooleanField()
    is_ai_eligible = serializers.BooleanField()
    ai_exclusion_reason = serializers.CharField()

    derived_objects = DerivedDicomObjectSerializer(
        many=True
    )


class KeyImageSelectedBySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()


class KeyImageSerializer(serializers.Serializer):
    key_image_id = serializers.UUIDField()
    study_id = serializers.UUIDField()
    sop_instance_uid = serializers.CharField()

    frame_number = serializers.IntegerField(
        allow_null=True
    )

    label = serializers.CharField()

    selected_by = KeyImageSelectedBySerializer()
    selected_at = serializers.DateTimeField()


class KeyImageListSerializer(serializers.Serializer):
    results = KeyImageSerializer(many=True)


class KeyImageCreateSerializer(serializers.Serializer):
    sop_instance_uid = serializers.CharField(
        max_length=64
    )
    frame_number = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )
    label = serializers.CharField(
        max_length=255
    )

    def validate_label(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "label is required."
            )

        return value
