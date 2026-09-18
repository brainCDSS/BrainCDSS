from rest_framework import serializers


class AssessmentWorklistPatientSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    sex = serializers.CharField(allow_null=True)
    estimated_age = serializers.IntegerField(allow_null=True)


class AssessmentWorklistItemSerializer(serializers.Serializer):
    assessment_id = serializers.UUIDField(allow_null=True)
    encounter_id = serializers.UUIDField()
    encounter_type = serializers.CharField()
    patient_summary = AssessmentWorklistPatientSerializer()
    status = serializers.CharField()
    triage_priority = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class AssessmentWorklistResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = AssessmentWorklistItemSerializer(many=True)


class AssessmentNeurologyDepartmentSerializer(serializers.Serializer):
    neurology_department_id = serializers.UUIDField(allow_null=True)


class AssessmentEncounterQuerySerializer(serializers.Serializer):
    encounter_id = serializers.UUIDField(required=True)


class AssessmentDetailItemSerializer(serializers.Serializer):
    item_code = serializers.CharField()
    value_text = serializers.CharField(allow_null=True)
    value_numeric = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )
    unit = serializers.CharField(allow_null=True)
    score = serializers.IntegerField(allow_null=True)
    is_red_flag = serializers.BooleanField()
    note = serializers.CharField(allow_null=True)


class AssessmentEncounterListItemSerializer(serializers.Serializer):
    assessment_id = serializers.UUIDField()
    encounter_id = serializers.UUIDField()
    status = serializers.CharField()
    total_score = serializers.IntegerField(allow_null=True)
    triage_priority = serializers.CharField(allow_null=True)
    onset_at = serializers.DateTimeField(allow_null=True)
    lkw_at = serializers.DateTimeField(allow_null=True)
    symptom_note = serializers.CharField(allow_null=True)
    assigned_neurologist = serializers.DictField(allow_null=True)
    items = AssessmentDetailItemSerializer(many=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AssessmentEncounterListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = AssessmentEncounterListItemSerializer(many=True)


class EmergencyWorklistPatientSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    sex = serializers.CharField(allow_null=True)
    estimated_age = serializers.IntegerField(allow_null=True)
    birth_date = serializers.DateField(allow_null=True)
    allergy_info = serializers.CharField(allow_null=True)


class EmergencyRedFlagSerializer(serializers.Serializer):
    item_code = serializers.CharField()
    value_text = serializers.CharField(allow_null=True)
    value_numeric = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True,
    )
    unit = serializers.CharField(allow_null=True)
    score = serializers.IntegerField(allow_null=True)
    note = serializers.CharField(allow_null=True)


class EmergencyWorklistEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    notified_at = serializers.DateTimeField(allow_null=True)
    acknowledged_at = serializers.DateTimeField(allow_null=True)


class EmergencyWorklistItemSerializer(serializers.Serializer):
    assessment_id = serializers.UUIDField()
    encounter_id = serializers.UUIDField()
    patient_summary = EmergencyWorklistPatientSerializer()
    total_score = serializers.IntegerField(allow_null=True)
    triage_priority = serializers.CharField()
    onset_at = serializers.DateTimeField(allow_null=True)
    lkw_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    symptom_note = serializers.CharField(allow_null=True)
    assigned_neurologist = serializers.DictField(allow_null=True)
    red_flags = EmergencyRedFlagSerializer(many=True)
    event = EmergencyWorklistEventSerializer()


class EmergencyWorklistResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = EmergencyWorklistItemSerializer(many=True)


class EmergencyEventAcknowledgeResponseSerializer(serializers.Serializer):
    event_id = serializers.UUIDField()
    status = serializers.CharField()
    acknowledged_by = serializers.UUIDField()
    acknowledged_at = serializers.DateTimeField()



class TriageReviewCreateSerializer(serializers.Serializer):
    priority = serializers.ChoiceField(
        choices=("EMERGENCY", "URGENT", "NON_EMERGENCY"),
    )
    reason = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        max_length=2000,
    )


class TriageReviewItemSerializer(serializers.Serializer):
    review_id = serializers.UUIDField()
    assessment_id = serializers.UUIDField()
    priority = serializers.CharField()
    reason = serializers.CharField()
    reviewer = serializers.DictField()
    reviewer_role = serializers.CharField()
    created_at = serializers.DateTimeField()


class TriageReviewListResponseSerializer(serializers.Serializer):
    initial_priority = serializers.CharField(allow_null=True)
    effective_priority = serializers.CharField(allow_null=True)
    latest_review = TriageReviewItemSerializer(allow_null=True)
    reviews = TriageReviewItemSerializer(many=True)
