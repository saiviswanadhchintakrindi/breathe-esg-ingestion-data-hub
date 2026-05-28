import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from ingestion.models import NormalizedRecord, Facility, EmissionFactor, AuditLog

def clean_row_value(val):
    return val.strip() if val else ''

def parse_utility_export(raw_source):
    """
    Parses a utility portal CSV export.
    Example columns:
    Account Number,Meter ID,Billing Start Date,Billing End Date,Usage (kWh),Total Bill ($),Tariff Code
    12345678,MTR-8890,2025-10-15,2025-11-13,3000,450.00,E-19
    """
    organization = raw_source.organization
    payload = raw_source.raw_payload
    logs = []
    
    # Setup CSV reader
    csv_file = io.StringIO(payload)
    reader = csv.reader(csv_file)
    
    # Read headers
    try:
        headers = next(reader)
    except StopIteration:
        raw_source.status = 'FAILED'
        raw_source.processing_logs = "Empty CSV payload."
        raw_source.save()
        return

    # Normalize headers
    headers = [h.strip().lower() for h in headers]
    logs.append(f"Parsed CSV headers: {headers}")

    # Column Mapping Dictionary
    # Handle variations in naming (e.g. Account Number vs Account ID)
    col_map = {}
    for idx, h in enumerate(headers):
        if 'account' in h:
            col_map['account'] = idx
        elif 'meter' in h:
            col_map['meter'] = idx
        elif 'start' in h:
            col_map['start_date'] = idx
        elif 'end' in h:
            col_map['end_date'] = idx
        elif 'usage' in h or 'kwh' in h:
            col_map['usage'] = idx
        elif 'bill' in h or 'charge' in h or 'cost' in h:
            col_map['bill_amount'] = idx
        elif 'tariff' in h or 'rate' in h:
            col_map['tariff'] = idx

    required_keys = ['start_date', 'end_date', 'usage']
    missing = [req for req in required_keys if req not in col_map]
    if missing:
        raw_source.status = 'FAILED'
        raw_source.processing_logs = f"Missing required CSV columns. Found headers: {headers}. Missing mapping for: {missing}"
        raw_source.save()
        return

    created_records_count = 0
    failed_records_count = 0
    
    for row_idx, row in enumerate(reader, start=1):
        if not row or not any(row):
            continue
            
        # Pad row if short
        if len(row) < len(headers):
            row += [''] * (len(headers) - len(row))
            
        anomalies_list = []
        is_failed = False
        is_suspicious = False
        
        # Extract fields using col_map
        raw_start = row[col_map['start_date']].strip()
        raw_end = row[col_map['end_date']].strip()
        raw_usage = row[col_map['usage']].strip()
        
        meter_id = row[col_map['meter']].strip() if 'meter' in col_map else ''
        account_no = row[col_map['account']].strip() if 'account' in col_map else ''
        raw_bill = row[col_map['bill_amount']].strip() if 'bill_amount' in col_map else '0.00'
        tariff_code = row[col_map['tariff']].strip() if 'tariff' in col_map else ''
        
        # 1. Parse Dates
        start_date = None
        end_date = None
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y'):
            if not start_date:
                try:
                    start_date = datetime.strptime(raw_start, fmt).date()
                except ValueError:
                    pass
            if not end_date:
                try:
                    end_date = datetime.strptime(raw_end, fmt).date()
                except ValueError:
                    pass
                    
        if not start_date or not end_date:
            is_failed = True
            anomalies_list.append(f"Invalid date formats: Start '{raw_start}', End '{raw_end}'. Use YYYY-MM-DD or MM/DD/YYYY.")
        
        # 2. Parse Usage
        usage_kwh = Decimal('0')
        try:
            usage_kwh = Decimal(raw_usage.replace(',', ''))
            if usage_kwh <= 0:
                is_suspicious = True
                anomalies_list.append("Usage is zero or negative.")
        except (InvalidOperation, ValueError):
            is_failed = True
            anomalies_list.append(f"Invalid usage value '{raw_usage}'")

        # 3. Parse Bill Amount
        bill_usd = Decimal('0')
        try:
            bill_usd = Decimal(raw_bill.replace('$', '').replace(',', '').strip())
        except (InvalidOperation, ValueError):
            is_suspicious = True
            anomalies_list.append(f"Invalid bill amount '{raw_bill}'")

        # 4. Plant/Facility lookup by Meter ID or Account No
        facility = None
        if meter_id:
            facility = Facility.objects.filter(organization=organization, facility_code=meter_id).first()
        if not facility and account_no:
            facility = Facility.objects.filter(organization=organization, facility_code=account_no).first()
            
        if not facility:
            is_suspicious = True
            anomalies_list.append(f"No Facility matches Meter ID '{meter_id}' or Account '{account_no}'")

        # 5. Handle Temporal Pro-Rating & Normalization
        if is_failed:
            # Create a single failed record for analysts to fix
            rec = NormalizedRecord.objects.create(
                organization=organization,
                raw_source=raw_source,
                facility=facility,
                scope=2,
                category="Purchased Electricity",
                activity_type="Electricity",
                activity_date=timezone.now().date(),
                original_quantity=usage_kwh,
                original_unit="kWh",
                normalized_quantity=usage_kwh,
                normalized_unit="kWh",
                emission_factor_value=Decimal('0.000000'),
                emission_factor_unit="tCO2e/kWh",
                emissions_tco2e=Decimal('0.000000'),
                status='FAILED',
                anomalies="; ".join(anomalies_list),
                is_locked=False
            )
            AuditLog.objects.create(
                organization=organization,
                record=rec,
                action='INGEST',
                new_values={'status': 'FAILED', 'anomalies': "; ".join(anomalies_list)}
            )
            failed_records_count += 1
            continue

        # Pro-rating calculation
        delta = end_date - start_date
        billing_days = delta.days + 1  # Inclusive of start and end dates
        
        if billing_days <= 0:
            is_failed = True
            rec = NormalizedRecord.objects.create(
                organization=organization,
                raw_source=raw_source,
                facility=facility,
                scope=2,
                category="Purchased Electricity",
                activity_type="Electricity",
                activity_date=start_date,
                original_quantity=usage_kwh,
                original_unit="kWh",
                normalized_quantity=usage_kwh,
                normalized_unit="kWh",
                emission_factor_value=Decimal('0.000000'),
                emission_factor_unit="tCO2e/kWh",
                emissions_tco2e=Decimal('0.000000'),
                status='FAILED',
                anomalies="Billing End Date must be after Billing Start Date.",
                is_locked=False
            )
            failed_records_count += 1
            continue

        if billing_days > 45:
            is_suspicious = True
            anomalies_list.append(f"Billing period is unusually long ({billing_days} days). Expecting ~30 days.")

        # Allocate usage and charges daily
        daily_usage = usage_kwh / Decimal(billing_days)
        
        # Apply facility-based Grid Emission Factor lookup
        # Default Scope 2 Grid factor: ~0.000385 tCO2e/kWh (US average)
        grid_factor = Decimal('0.000385')
        ef_source = "US EPA eGRID (National Average)"
        
        # If facility is mapped, search for specific grid subregion factors
        if facility:
            loc = facility.grid_subregion or facility.location
            # Query factors database
            ef = EmissionFactor.objects.filter(
                scope=2,
                category="Purchased Electricity",
                activity_type="Electricity - Grid",
                factor_unit="tCO2e/kWh"
            ).filter(source__icontains=loc).first()
            
            if not ef:
                # Also try location code directly
                ef = EmissionFactor.objects.filter(
                    scope=2,
                    category="Purchased Electricity",
                    activity_type="Electricity - Grid",
                    factor_unit="tCO2e/kWh"
                ).first() # Fallback to first factor
                
            if ef:
                grid_factor = ef.factor_value
                ef_source = ef.source
            else:
                anomalies_list.append(f"No specific grid emission factor found for facility subregion '{loc}'. Used national average.")

        # Create NormalizedRecord for each day in the billing cycle
        anomalies_text = "; ".join(anomalies_list) if anomalies_list else ""
        record_status = 'SUSPICIOUS' if is_suspicious else 'PENDING_REVIEW'
        
        for d in range(billing_days):
            current_day = start_date + timedelta(days=d)
            daily_emissions = daily_usage * grid_factor
            
            rec = NormalizedRecord.objects.create(
                organization=organization,
                raw_source=raw_source,
                facility=facility,
                scope=2,
                category="Purchased Electricity",
                activity_type="Electricity - Grid",
                activity_date=current_day,
                original_quantity=usage_kwh,  # Retain reference to total bill quantity
                original_unit="kWh (Bill Total)",
                normalized_quantity=daily_usage, # Store daily allocated usage
                normalized_unit="kWh",
                emission_factor_value=grid_factor,
                emission_factor_unit="tCO2e/kWh",
                emissions_tco2e=daily_emissions,
                status=record_status,
                anomalies=anomalies_text,
                is_locked=False,
                comments=f"Daily pro-rated slice {d+1}/{billing_days} of bill {start_date} to {end_date} (Total: {usage_kwh} kWh)"
            )
            
            # Audit trail
            AuditLog.objects.create(
                organization=organization,
                record=rec,
                action='INGEST',
                new_values={
                    'scope': 2,
                    'category': "Purchased Electricity",
                    'activity_date': str(current_day),
                    'original_quantity': str(usage_kwh),
                    'original_unit': 'kWh (Bill Total)',
                    'normalized_quantity': str(daily_usage),
                    'normalized_unit': 'kWh',
                    'emissions_tco2e': str(daily_emissions),
                    'status': record_status,
                    'anomalies': anomalies_text,
                }
            )
            created_records_count += 1
            
    # Update raw source logs
    raw_source.processing_logs = (
        f"Parsed Utility CSV. Created daily allocation records: {created_records_count}. "
        f"Failed billing records: {failed_records_count}."
    )
    if failed_records_count > 0 and created_records_count > 0:
        raw_source.status = 'PARTIAL'
    elif failed_records_count > 0:
        raw_source.status = 'FAILED'
    else:
        raw_source.status = 'SUCCESS'
    raw_source.save()
