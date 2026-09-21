from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer

from apps.patients.models import Patient


SEX_VALUES = ("M", "F", "U")
PREGNANCY_STATUS_VALUES = (
    "UNKNOWN",
    "NOT_PREGNANT",
    "PREGNANT",
)

NAME_MAX_LENGTH = (
    Patient._meta.get_field("name").max_length
)
PHONE_MAX_LENGTH = (
    Patient._meta.get_field("phone").max_length
)
EMERGENCY_CONTACT_MAX_LENGTH = (
    Patient._meta.get_field(
        "emergency_contact"
    ).max_length
)


class PatientListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    patient_no = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    birth_date = serializers.DateField(required=False)
    status = serializers.ChoiceField(
        required=False,
        choices=("ACTIVE", "TEMP", "MERGED"),
    )
    scope = serializers.ChoiceField(
        required=False,
        choices=("all", "mine"),
        default="all",
    )

    page = serializers.IntegerField(
        required=False,
        min_value=1,
        default=1,
    )


class PatientCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=NAME_MAX_LENGTH,
        allow_blank=False,
    )
    birth_date = serializers.DateField()
    sex = serializers.ChoiceField(choices=SEX_VALUES)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=PHONE_MAX_LENGTH,
    )
    emergency_contact = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=EMERGENCY_CONTACT_MAX_LENGTH,
    )

    def validate_name(self, value):
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError(
                "name is required."
            )
        return normalized

    def validate_birth_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "birth_date cannot be in the future."
            )
        return value


class TemporaryPatientCreateSerializer(serializers.Serializer):
    sex = serializers.ChoiceField(
        required=False,
        allow_null=True,
        choices=SEX_VALUES,
    )
    estimated_age = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=150,
    )


class PatientUpdateSerializer(serializers.Serializer):
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=PHONE_MAX_LENGTH,
    )
    emergency_contact = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=EMERGENCY_CONTACT_MAX_LENGTH,
    )
    pregnancy_status = serializers.ChoiceField(
        required=False,
        choices=PREGNANCY_STATUS_VALUES,
    )

    def validate(self, attrs):
        allowed = {
            "phone",
            "emergency_contact",
            "pregnancy_status",
        }
        unknown = set(self.initial_data) - allowed

        if unknown:
            raise serializers.ValidationError({
                "unknown_fields": sorted(unknown)
            })

        if not attrs:
            raise serializers.ValidationError(
                "At least one updatable field is required."
            )

        return attrs


class PatientMergeSerializer(serializers.Serializer):
    target_patient_id = serializers.UUIDField()


class PatientIdentifySerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=NAME_MAX_LENGTH,
        allow_blank=False,
    )
    birth_date = serializers.DateField()
    sex = serializers.ChoiceField(choices=SEX_VALUES)
    phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=PHONE_MAX_LENGTH,
    )
    emergency_contact = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=EMERGENCY_CONTACT_MAX_LENGTH,
    )

    def validate_name(self, value):
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError(
                "name is required."
            )
        return normalized

    def validate_birth_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError(
                "birth_date cannot be in the future."
            )
        return value


# ------------------------------------------------------------------
# Response serializers: used by drf-spectacular to keep these 10
# real APIs out of the generated "unable to guess serializer" errors.
# ------------------------------------------------------------------

class PatientListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    estimated_age = serializers.IntegerField(allow_null=True)
    sex = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    allergy_info = serializers.CharField(
        allow_null=True,
        allow_blank=True,
    )
    status = serializers.CharField()


class PatientListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = PatientListItemSerializer(many=True)


class PatientCreateResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    estimated_age = serializers.IntegerField(allow_null=True)
    sex = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    emergency_contact = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


@extend_schema_serializer(component_name="PatientActorSummary")
class UserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class TemporaryPatientResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    estimated_age = serializers.IntegerField(allow_null=True)
    sex = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    created_by = UserSummarySerializer()
    created_at = serializers.DateTimeField()


class MergedIntoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()


class PatientDetailResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    estimated_age = serializers.IntegerField(allow_null=True)
    sex = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    emergency_contact = serializers.CharField(allow_null=True)
    allergy_info = serializers.CharField(
        allow_null=True,
        allow_blank=True,
    )
    pregnancy_status = serializers.CharField()
    pregnancy_status_updated_at = serializers.DateTimeField(
        allow_null=True
    )
    status = serializers.CharField()

    latest_assessment = serializers.DictField(
        allow_null=True,
    )
    merged_into = MergedIntoSerializer(allow_null=True)
    resolved_from_patient_id = serializers.UUIDField(
        allow_null=True
    )
    merged_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class PatientUpdateResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField(allow_null=True)
    sex = serializers.CharField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    emergency_contact = serializers.CharField(allow_null=True)
    pregnancy_status = serializers.CharField()
    pregnancy_status_updated_at = serializers.DateTimeField(
        allow_null=True
    )
    status = serializers.CharField()
    updated_at = serializers.DateTimeField()


class MergeSourcePatientSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    status = serializers.CharField()
    merged_into_patient_id = serializers.UUIDField()


class MergeTargetPatientSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    status = serializers.CharField()


class PatientMergeResponseSerializer(serializers.Serializer):
    merge_history_id = serializers.UUIDField()
    source_patient = MergeSourcePatientSerializer()
    target_patient = MergeTargetPatientSerializer()
    migrated_fk_summary = serializers.DictField(
        child=serializers.IntegerField()
    )
    merged_by = UserSummarySerializer()
    merged_at = serializers.DateTimeField()
    outbox_event_id = serializers.UUIDField()


class PatientIdentifyResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    patient_no = serializers.CharField()
    name = serializers.CharField()
    birth_date = serializers.DateField()
    estimated_age = serializers.IntegerField(allow_null=True)
    sex = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    emergency_contact = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    updated_at = serializers.DateTimeField()


class FavoriteHospitalItemSerializer(serializers.Serializer):
    hospital_id = serializers.UUIDField()
    name = serializers.CharField()
    address = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=7,
        allow_null=True,
    )
    created_at = serializers.DateTimeField()


class FavoriteHospitalListResponseSerializer(serializers.Serializer):
    results = FavoriteHospitalItemSerializer(many=True)


class FavoriteHospitalPutResponseSerializer(serializers.Serializer):
    hospital_id = serializers.UUIDField()
    favorite = serializers.BooleanField()
    created_at = serializers.DateTimeField()
