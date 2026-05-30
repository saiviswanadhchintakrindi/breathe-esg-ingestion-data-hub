import json
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from ingestion.models import Organization, Facility, RawIngestionSource, NormalizedRecord, AuditLog, EmissionFactor
from ingestion.serializers import (
    OrganizationSerializer, FacilitySerializer, RawIngestionSourceSerializer,
    NormalizedRecordSerializer, AuditLogSerializer
)
from ingestion.parsers.sap_parser import parse_sap_export
from ingestion.parsers.utility_parser import parse_utility_export
from ingestion.parsers.travel_parser import parse_travel_export

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

class FacilityViewSet(viewsets.ModelViewSet):
    serializer_class = FacilitySerializer

    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if org_id:
            return Facility.objects.filter(organization_id=org_id)
        return Facility.objects.all()

class RawIngestionSourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RawIngestionSourceSerializer

    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if org_id:
            return RawIngestionSource.objects.filter(organization_id=org_id).order_by('-ingested_at')
        return RawIngestionSource.objects.all().order_by('-ingested_at')

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        if org_id:
            return AuditLog.objects.filter(organization_id=org_id).order_by('-timestamp')
        return AuditLog.objects.all().order_by('-timestamp')

class NormalizedRecordViewSet(viewsets.ModelViewSet):
    serializer_class = NormalizedRecordSerializer

    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        queryset = NormalizedRecord.objects.all()
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
            
        # Optional filters
        scope = self.request.query_params.get('scope')
        if scope:
            queryset = queryset.filter(scope=scope)
            
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        source_type = self.request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(raw_source__source_type=source_type)
            
        facility_id = self.request.query_params.get('facility_id')
        if facility_id:
            queryset = queryset.filter(facility_id=facility_id)
            
        search = self.request.query_params.get('search')
       if search:
            queryset = queryset.filter(
                Q(category__icontains=search) | 
                Q(activity_type__icontains=search) |
                Q(anomalies__icontains=search) |
                Q(comments__icontains=search)
            )
            
        return queryset.order_by('-activity_date')

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Enforce Audit Locking
        if instance.is_locked:
            return Response(
                {"error": "This record has been approved and locked for audit. It cannot be modified."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        change_reason = request.data.get('change_reason')
        if not change_reason:
            return Response(
                {"error": "A change reason is required to manually update carbon records."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Capture old values for Audit trail
        old_values = {
            'normalized_quantity': str(instance.normalized_quantity),
            'emission_factor_value': str(instance.emission_factor_value),
            'emissions_tco2e': str(instance.emissions_tco2e),
            'status': instance.status,
            'comments': instance.comments,
        }
        
        # Run standard update
        response = super().update(request, *args, **kwargs)
        
        # Refresh and do calculations
        instance.refresh_from_db()
        
        # Mark as edited
        instance.is_edited = True
        
        # Recompute carbon if quantity or factor was modified
        new_qty = Decimal(str(instance.normalized_quantity))
        new_ef = Decimal(str(instance.emission_factor_value))
        computed_emissions = new_qty * new_ef
        
        if instance.emissions_tco2e != computed_emissions:
            instance.emissions_tco2e = computed_emissions
            
        # If it was suspicious/failed and is updated, check if we resolve status
        # Analysts usually edit to fix discrepancies
        if instance.status in ('SUSPICIOUS', 'FAILED'):
            instance.status = 'PENDING_REVIEW'
            
        instance.save()
        
        # Record to Audit Log
        new_values = {
            'normalized_quantity': str(instance.normalized_quantity),
            'emission_factor_value': str(instance.emission_factor_value),
            'emissions_tco2e': str(instance.emissions_tco2e),
            'status': instance.status,
            'comments': instance.comments,
        }
        
        AuditLog.objects.create(
            organization=instance.organization,
            record=instance,
            user=request.user if request.user.is_authenticated else None,
            action='EDIT',
            old_values=old_values,
            new_values=new_values,
            change_reason=change_reason
        )
        
        # Re-serialize
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    @transaction.atomic
    def approve(self, request, pk=None):
        instance = self.get_object()
        
        if instance.status == 'FAILED':
            return Response(
                {"error": "Failed validation records must be corrected before approval."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if instance.is_locked:
            return Response(
                {"error": "Record is already approved and locked."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        old_status = instance.status
        instance.status = 'APPROVED'
        instance.is_locked = True
        instance.reviewed_by = request.user if request.user.is_authenticated else None
        instance.reviewed_at = timezone.now()
        instance.save()
        
        AuditLog.objects.create(
            organization=instance.organization,
            record=instance,
            user=request.user if request.user.is_authenticated else None,
            action='APPROVE',
            old_values={'status': old_status, 'is_locked': False},
            new_values={'status': 'APPROVED', 'is_locked': True},
            change_reason="Analyst signed off and locked row for auditor audit trail."
        )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reject')
    @transaction.atomic
    def reject(self, request, pk=None):
        instance = self.get_object()
        
        if instance.is_locked:
            return Response(
                {"error": "Locked records cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        old_status = instance.status
        instance.status = 'REJECTED'
        instance.save()
        
        AuditLog.objects.create(
            organization=instance.organization,
            record=instance,
            user=request.user if request.user.is_authenticated else None,
            action='REJECT',
            old_values={'status': old_status},
            new_values={'status': 'REJECTED'},
            change_reason=request.data.get('change_reason', 'Analyst rejected record.')
        )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class IngestAPIView(APIView):
    def post(self, request, *args, **kwargs):
        org_id = request.data.get('organization_id')
        source_type = request.data.get('source_type')
        
        if not org_id or not source_type:
            return Response(
                {"error": "Missing organization_id or source_type in ingestion request."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response(
                {"error": f"Organization with ID {org_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        filename = None
        raw_payload = ""
        
        if source_type in ('SAP', 'UTILITY'):
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {"error": f"A file upload is required for source type {source_type}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            filename = uploaded_file.name
            try:
                # Read file payload
                raw_payload = uploaded_file.read().decode('utf-8')
            except Exception as e:
                return Response(
                    {"error": f"Failed to read file encoding: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif source_type == 'TRAVEL':
            # Travel is a simulated API pull. We can read it from JSON request
            raw_payload = request.data.get('raw_payload')
            if not raw_payload:
                return Response(
                    {"error": "raw_payload field is required for Travel JSON API Simulation."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # If they pass a JSON object, convert to string
            if not isinstance(raw_payload, str):
                raw_payload = json.dumps(raw_payload)
            filename = "simulated_api_concur_pull.json"
        else:
            return Response(
                {"error": f"Unsupported source type '{source_type}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 1. Store Raw Payload as Source of Truth
        raw_source = RawIngestionSource.objects.create(
            organization=organization,
            source_type=source_type,
            filename=filename,
            raw_payload=raw_payload,
            status='SUCCESS', # Defaults, parser will modify
            ingested_by=request.user if request.user.is_authenticated else None
        )
        
        # 2. Invoke appropriate parser synchronously for UI immediate response
        try:
            if source_type == 'SAP':
                parse_sap_export(raw_source)
            elif source_type == 'UTILITY':
                parse_utility_export(raw_source)
            elif source_type == 'TRAVEL':
                parse_travel_export(raw_source)
        except Exception as parser_err:
            raw_source.status = 'FAILED'
            raw_source.processing_logs = f"Fatal Parsing Exception: {str(parser_err)}"
            raw_source.save()
            return Response(
                {
                    "error": "Parser encountered a critical processing exception.",
                    "details": str(parser_err),
                    "raw_source_id": raw_source.id
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Re-fetch raw source to get updated processing logs/stats
        raw_source.refresh_from_db()
        
        return Response({
            "message": "Ingestion process completed.",
            "raw_source": RawIngestionSourceSerializer(raw_source).data,
            "records_count": raw_source.records.count()
        }, status=status.HTTP_201_CREATED)


class DashboardSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        org_id = request.query_params.get('org_id')
        if not org_id:
            return Response(
                {"error": "org_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Filter active organization records (excluding FAILED ones from statistics)
        base_records = NormalizedRecord.objects.filter(organization_id=org_id)
        valid_records = base_records.exclude(status='FAILED')
        
        # KPI calculations
        total_emissions = valid_records.aggregate(total=Sum('emissions_tco2e'))['total'] or Decimal('0')
        total_approved = valid_records.filter(status='APPROVED').aggregate(total=Sum('emissions_tco2e'))['total'] or Decimal('0')
        
        record_counts = base_records.values('status').annotate(count=Count('id'))
        counts_dict = {item['status']: item['count'] for item in record_counts}
        
        # Scope breakdown
        scope_breakdown = valid_records.values('scope').annotate(emissions=Sum('emissions_tco2e')).order_by('scope')
        scope_data = {f"Scope {item['scope']}": item['emissions'] for item in scope_breakdown}
        
        # Facility breakdown
        facility_breakdown = valid_records.values(
            fac_id=F('facility__id'), 
            facility_name=F('facility__name')
        ).annotate(
            emissions=Sum('emissions_tco2e')
        ).order_by('-emissions')
        
        facility_data = [
            {
                "id": f['fac_id'] or 0, 
                "name": f['facility_name'] or "Corporate / Scope 3", 
                "emissions": f['emissions']
            }
            for f in facility_breakdown
        ]
        
        # Category breakdown
        category_breakdown = valid_records.values('category').annotate(
            emissions=Sum('emissions_tco2e')
        ).order_by('-emissions')
        
        category_data = [
            {"category": c['category'], "emissions": c['emissions']}
            for c in category_breakdown
        ]
        
        # Historical Trend (Pro-rated allocations grouped by month)
        # Using TruncMonth to aggregate across dates
        monthly_trend = valid_records.annotate(
            month=TruncMonth('activity_date')
        ).values('month').annotate(
            emissions=Sum('emissions_tco2e')
        ).order_by('month')
        
        trend_data = [
            {
                "month": item['month'].strftime('%Y-%m') if item['month'] else 'N/A', 
                "emissions": item['emissions']
            }
            for item in monthly_trend
        ]
        
        return Response({
            "total_emissions": total_emissions,
            "approved_emissions": total_approved,
            "counts": {
                "pending": counts_dict.get('PENDING_REVIEW', 0),
                "approved": counts_dict.get('APPROVED', 0),
                "rejected": counts_dict.get('REJECTED', 0),
                "suspicious": counts_dict.get('SUSPICIOUS', 0),
                "failed": counts_dict.get('FAILED', 0),
                "total": base_records.count()
            },
            "scopes": scope_data,
            "facilities": facility_data,
            "categories": category_data,
            "monthly_trend": trend_data
        })
