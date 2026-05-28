from django.contrib import admin
from ingestion.models import Organization, UserProfile, Facility, IataAirport, EmissionFactor, RawIngestionSource, NormalizedRecord, AuditLog

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organization', 'role')
    list_filter = ('role', 'organization')

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'facility_code', 'name', 'location', 'organization')
    list_filter = ('organization', 'location')

@admin.register(IataAirport)
class IataAirportAdmin(admin.ModelAdmin):
    list_display = ('iata_code', 'city', 'country', 'latitude', 'longitude')
    search_fields = ('iata_code', 'city', 'country')

@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ('id', 'scope', 'category', 'activity_type', 'factor_value', 'factor_unit', 'year', 'organization')
    list_filter = ('scope', 'category', 'year', 'organization')
    search_fields = ('activity_type', 'category')

@admin.register(RawIngestionSource)
class RawIngestionSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_type', 'filename', 'ingested_at', 'status', 'organization')
    list_filter = ('source_type', 'status', 'organization')
    readonly_fields = ('raw_payload',)

@admin.register(NormalizedRecord)
class NormalizedRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'scope', 'category', 'activity_type', 'activity_date', 'emissions_tco2e', 'status', 'is_locked')
    list_filter = ('status', 'scope', 'category', 'is_locked', 'organization')
    search_fields = ('activity_type', 'comments', 'anomalies')
    readonly_fields = ('raw_source',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'record', 'action', 'user', 'timestamp', 'organization')
    list_filter = ('action', 'organization')
    readonly_fields = ('old_values', 'new_values')
