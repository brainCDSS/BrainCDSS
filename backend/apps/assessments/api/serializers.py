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
