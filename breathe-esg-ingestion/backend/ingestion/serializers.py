from rest_framework import serializers
from ingestion.models import Organization, Facility, RawIngestionSource, NormalizedRecord, AuditLog, EmissionFactor
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = '__all__'

class RawIngestionSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawIngestionSource
        fields = '__all__'

class NormalizedRecordSerializer(serializers.ModelSerializer):
    facility_details = FacilitySerializer(source='facility', read_only=True)
    raw_source_details = RawIngestionSourceSerializer(source='raw_source', read_only=True)
    reviewed_by_name = serializers.ReadOnlyField(source='reviewed_by.username')
    
    class Meta:
        model = NormalizedRecord
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    record_label = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = '__all__'

    def get_record_label(self, obj):
        return f"{obj.record.category} ({obj.record.activity_date})"
