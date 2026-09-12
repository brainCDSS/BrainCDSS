from rest_framework import serializers


class HospitalListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    lat = serializers.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        min_value=-90,
        max_value=90,
    )
    lng = serializers.DecimalField(
        required=False,
        max_digits=9,
        decimal_places=6,
        min_value=-180,
        max_value=180,
    )
    page = serializers.IntegerField(required=False, min_value=1, default=1)

    def validate(self, attrs):
        lat_present = "lat" in attrs
        lng_present = "lng" in attrs

        if lat_present != lng_present:
            raise serializers.ValidationError(
                "lat and lng must be supplied together."
            )

        return attrs


class ClinicianListQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)


class HospitalListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
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
    distance_km = serializers.FloatField(allow_null=True)
    is_favorite = serializers.BooleanField()


class HospitalListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = HospitalListItemSerializer(many=True)


class DepartmentItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()


class HospitalDetailResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
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
    departments = DepartmentItemSerializer(many=True)
    is_favorite = serializers.BooleanField()


class HospitalSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class HospitalDepartmentResponseSerializer(serializers.Serializer):
    hospital = HospitalSummarySerializer()
    departments = DepartmentItemSerializer(many=True)


class DepartmentSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ClinicianItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    specialty = serializers.CharField(allow_null=True)
    license_no = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()


class DepartmentClinicianResponseSerializer(serializers.Serializer):
    department = DepartmentSummarySerializer()
    clinicians = ClinicianItemSerializer(many=True)
