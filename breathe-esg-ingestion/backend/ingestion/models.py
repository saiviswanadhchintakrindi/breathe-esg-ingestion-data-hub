from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ANALYST', 'Analyst'),
        ('ADMIN', 'Administrator'),
        ('AUDITOR', 'Auditor'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ANALYST')

    def __str__(self):
        return f"{self.user.username} ({self.role}) - {self.organization.name}"

class Facility(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='facilities')
    facility_code = models.CharField(max_length=100, help_text="Matches external codes like SAP WERKS or Meter IDs")
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=100, help_text="e.g. US, DE, IN")
    grid_subregion = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. CAMX, DE-grid")

    class Meta:
        unique_together = ('organization', 'facility_code')

    def __str__(self):
        return f"{self.name} ({self.facility_code}) - {self.organization.name}"

class IataAirport(models.Model):
    iata_code = models.CharField(max_length=3, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.iata_code} - {self.city}, {self.country}"

class EmissionFactor(models.Model):
    SCOPE_CHOICES = [
        (1, 'Scope 1'),
        (2, 'Scope 2'),
        (3, 'Scope 3'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='custom_emission_factors')
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=150)
    factor_value = models.DecimalField(max_digits=12, decimal_places=6, help_text="Value in metric tonnes of CO2e per unit")
    factor_unit = models.CharField(max_length=50, help_text="e.g. tCO2e/kWh, tCO2e/liter, tCO2e/passenger-km")
    source = models.CharField(max_length=255)
    year = models.IntegerField()

    def __str__(self):
        scope_str = f"Scope {self.scope}"
        return f"{scope_str} - {self.activity_type}: {self.factor_value} {self.factor_unit} ({self.year})"

class RawIngestionSource(models.Model):
    SOURCE_CHOICES = [
        ('SAP', 'SAP ERP (Fuel/Procurement)'),
        ('UTILITY', 'Utility Portal Export (Electricity)'),
        ('TRAVEL', 'Corporate Travel Platform (Concur API)'),
    ]
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='ingestion_sources')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=255, blank=True, null=True)
    raw_payload = models.TextField(help_text="Original contents of file or API JSON payload")
    ingested_at = models.DateTimeField(auto_now_add=True)
    ingested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCESS')
    processing_logs = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_source_type_display()} - {self.ingested_at.strftime('%Y-%m-%d %H:%M:%S')}"

class NormalizedRecord(models.Model):
    STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPICIOUS', 'Suspicious'),
        ('FAILED', 'Failed Validation'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='records')
    raw_source = models.ForeignKey(RawIngestionSource, on_delete=models.CASCADE, related_name='records')
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name='records')
    scope = models.IntegerField(choices=EmissionFactor.SCOPE_CHOICES)
    category = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=150)
    activity_date = models.DateField(help_text="Specific calendar date this activity took place")
    
    # Original Data Traceability
    original_quantity = models.DecimalField(max_digits=15, decimal_places=4)
    original_unit = models.CharField(max_length=50)
    
    # Normalized Data
    normalized_quantity = models.DecimalField(max_digits=15, decimal_places=4)
    normalized_unit = models.CharField(max_length=50)
    
    # Emissions Math
    emission_factor_value = models.DecimalField(max_digits=12, decimal_places=6)
    emission_factor_unit = models.CharField(max_length=50)
    emissions_tco2e = models.DecimalField(max_digits=15, decimal_places=6)
    
    # Sign-off & Audit state
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    anomalies = models.TextField(blank=True, null=True, help_text="Detailed error messages or warning flags")
    is_locked = models.BooleanField(default=False, help_text="True if approved, blocking further edits for audit")
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False, help_text="Flagged if values were updated manually after ingestion")
    comments = models.TextField(blank=True, null=True, help_text="Analyst commentary or explanation for edits")
    client_environment = models.CharField(max_length=100, blank=True, null=True, help_text="Client environment tag e.g. Production, Staging, Dev, UAT")

    def __str__(self):
        return f"{self.category} ({self.activity_date}) - {self.emissions_tco2e} tCO2e"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('INGEST', 'Data Ingestion'),
        ('EDIT', 'Manual Edit'),
        ('APPROVE', 'Review & Approval'),
        ('REJECT', 'Rejection'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    record = models.ForeignKey(NormalizedRecord, on_delete=models.CASCADE, related_name='audits')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_values = models.JSONField(blank=True, null=True, help_text="JSON mapping of fields before changes")
    new_values = models.JSONField(blank=True, null=True, help_text="JSON mapping of fields after changes")
    change_reason = models.TextField(blank=True, null=True, help_text="Required explanation for manual adjustments")

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"{self.action} on Record #{self.record.id} by {user_str} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
