import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from ingestion.models import NormalizedRecord, Facility, EmissionFactor, AuditLog

GERMAN_HEADER_MAP = {
    'BUDAT': 'posting_date',
    'MATNR': 'material_number',
    'TXZ01': 'description',
    'MAKTX': 'description',
    'MENGE': 'quantity',
    'MEINS': 'unit',
    'DMBTR': 'amount',
    'WRBTR': 'amount',
    'WAERS': 'currency',
    'WERKS': 'plant',
    'LIFNR': 'vendor',
    'BELNR': 'doc_number',
}

UNIT_MAP = {
    'ltr': 'L',
    'l': 'L',
    'liter': 'L',
    'kg': 'KG',
    'kilogramm': 'KG',
    'to': 't',
    't': 't',
    'tonne': 't',
    'ton': 't',
    'm3': 'm3',
    'm³': 'm3',
    'st': 'pcs',
    'pc': 'pcs',
    'pcs': 'pcs',
    'stk': 'pcs',
}

# Fixed exchange rates for demo
EXCHANGE_RATES = {
    'USD': Decimal('1.00'),
    'EUR': Decimal('1.08'),
    'GBP': Decimal('1.27'),
}

def clean_row_value(val):
    return val.strip() if val else ''

def parse_sap_export(raw_source):
    """
    Parses a pipe-delimited SAP flat file.
    Example payload format:
    | BELNR | BUDAT | MATNR | TXZ01 | MENGE | MEINS | DMBTR | WAERS | WERKS | LIFNR |
    | 10001 | 15.10.2025 | M-01 | Diesel Kraftstoff | 5000.00 | Ltr | 6500.00 | EUR | 1000 | V-99 |
    """
    organization = raw_source.organization
    payload = raw_source.raw_payload
    logs = []
    
    # Read lines and strip empty leading/trailing pipes
    lines = []
    for line in payload.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        # Strip outer pipes if present
        if line_str.startswith('|'):
            line_str = line_str[1:]
        if line_str.endswith('|'):
            line_str = line_str[:-1]
        lines.append(line_str)

    if not lines:
        raw_source.status = 'FAILED'
        raw_source.processing_logs = "Empty payload or invalid format."
        raw_source.save()
        return

    # Parse headers
    header_line = lines[0]
    headers = [clean_row_value(h) for h in header_line.split('|')]
    
    # Map headers
    mapped_headers = []
    for h in headers:
        normalized_h = h.upper()
        mapped_h = GERMAN_HEADER_MAP.get(normalized_h, normalized_h.lower())
        mapped_headers.append(mapped_h)
        
    logs.append(f"Mapped headers: {dict(zip(headers, mapped_headers))}")

    # Required columns check
    required = ['posting_date', 'quantity', 'unit', 'amount', 'currency']
    missing = [req for req in required if req not in mapped_headers]
    if missing:
        raw_source.status = 'FAILED'
        raw_source.processing_logs = f"Missing required columns: {missing}. Headers parsed: {headers}"
        raw_source.save()
        return

    created_records_count = 0
    failed_records_count = 0
    
    for idx, line in enumerate(lines[1:], start=1):
        row_cells = [clean_row_value(c) for c in line.split('|')]
        # Pad row if cells are fewer than headers due to trailing blanks
        if len(row_cells) < len(mapped_headers):
            row_cells += [''] * (len(mapped_headers) - len(row_cells))
        elif len(row_cells) > len(mapped_headers):
            row_cells = row_cells[:len(mapped_headers)]

        row_dict = dict(zip(mapped_headers, row_cells))
        
        # Validation variables
        anomalies_list = []
        is_suspicious = False
        is_failed = False
        record_status = 'PENDING_REVIEW'
        
        # 1. Parse Date (BUDAT is DD.MM.YYYY in Germany)
        raw_date = row_dict.get('posting_date')
        parsed_date = None
        try:
            # Try German format first
            parsed_date = datetime.strptime(raw_date, '%d.%m.%Y').date()
        except ValueError:
            try:
                # Try standard ISO format
                parsed_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError:
                is_failed = True
                anomalies_list.append(f"Invalid date format '{raw_date}': Must be DD.MM.YYYY or YYYY-MM-DD")

        # 2. Parse Quantity and Amount
        raw_qty = row_dict.get('quantity')
        raw_amount = row_dict.get('amount')
        
        qty = Decimal('0')
        amount = Decimal('0')
        
        try:
            # Replace European decimal commas and thousands dots
            # Note: A real SAP export might be "5.000,00" or "5000.00"
            clean_qty_str = raw_qty.replace('.', '').replace(',', '.') if ',' in raw_qty else raw_qty
            qty = Decimal(clean_qty_str)
            if qty <= 0:
                is_suspicious = True
                anomalies_list.append("Quantity is zero or negative.")
        except (InvalidOperation, ValueError):
            is_failed = True
            anomalies_list.append(f"Invalid quantity '{raw_qty}'")

        try:
            clean_amt_str = raw_amount.replace('.', '').replace(',', '.') if ',' in raw_amount else raw_amount
            amount = Decimal(clean_amt_str)
            if amount < 0:
                is_suspicious = True
                anomalies_list.append("Amount spent is negative.")
        except (InvalidOperation, ValueError):
            is_failed = True
            anomalies_list.append(f"Invalid monetary amount '{raw_amount}'")

        # 3. Currency and Plant Lookup
        currency = row_dict.get('currency', 'USD').upper()
        plant_code = row_dict.get('plant', '')
        facility = None
        
        if plant_code:
            facility = Facility.objects.filter(organization=organization, facility_code=plant_code).first()
            if not facility:
                is_suspicious = True
                anomalies_list.append(f"Plant code '{plant_code}' not found in registered Facilities.")
        else:
            is_suspicious = True
            anomalies_list.append("Missing Plant Code (WERKS).")

        # 4. Material and Category Mapping
        material_desc = row_dict.get('description', '')
        material_num = row_dict.get('material_number', '')
        
        scope = 3
        category = "Procurement"
        activity_type = "Purchased Goods and Services (General)"
        factor_unit_match = "tCO2e/USD"
        
        desc_lower = material_desc.lower()
        
        # Simple heuristic to distinguish Fuel (Scope 1) vs general Procurement (Scope 3)
        is_fuel = False
        fuel_type = None
        
        if any(keyword in desc_lower for keyword in ['diesel', 'kraftstoff', 'gasoline', 'benzin', 'petrol', 'heating oil', 'heizol', 'heizöl']):
            is_fuel = True
            if 'diesel' in desc_lower or 'kraftstoff' in desc_lower:
                fuel_type = 'Diesel'
            elif 'gasoline' in desc_lower or 'benzin' in desc_lower or 'petrol' in desc_lower:
                fuel_type = 'Gasoline'
            elif 'heating' in desc_lower or 'heiz' in desc_lower:
                fuel_type = 'Heating Oil'
            else:
                fuel_type = 'Fuel (Other)'

        orig_unit = row_dict.get('unit', '')
        norm_unit = UNIT_MAP.get(orig_unit.lower(), orig_unit)
        
        factor_value = Decimal('0.000000')
        normalized_qty = qty
        
        if is_failed:
            record_status = 'FAILED'
        else:
            if is_fuel:
                scope = 1
                category = "Stationary Combustion"
                activity_type = fuel_type
                
                # Normalize units for Scope 1 fuels
                # Assume factors are in tCO2e/L
                if norm_unit == 'L':
                    normalized_qty = qty
                elif norm_unit == 't':
                    # Rough conversion for diesel density: 1 tonne = ~1190 Liters
                    normalized_qty = qty * Decimal('1190.0')
                    norm_unit = 'L'
                    anomalies_list.append("Unit converted from tonnes to Liters using density conversion.")
                elif norm_unit == 'm3':
                    # 1 m3 = 1000 Liters
                    normalized_qty = qty * Decimal('1000.0')
                    norm_unit = 'L'
                    anomalies_list.append("Unit converted from m3 to Liters.")
                else:
                    is_suspicious = True
                    anomalies_list.append(f"Unusual unit '{orig_unit}' for fuel stationary combustion.")
                    
                # Fetch fuel emission factor
                ef = EmissionFactor.objects.filter(
                    scope=1, 
                    category=category, 
                    activity_type=activity_type,
                    year=(parsed_date.year if parsed_date else 2025)
                ).first()
                if ef:
                    factor_value = ef.factor_value
                    factor_unit_match = ef.factor_unit
                else:
                    # System default backup
                    if fuel_type == 'Diesel':
                        factor_value = Decimal('0.00268')  # ~2.68 kg CO2e / L
                    elif fuel_type == 'Gasoline':
                        factor_value = Decimal('0.00231')  # ~2.31 kg CO2e / L
                    elif fuel_type == 'Heating Oil':
                        factor_value = Decimal('0.00252')
                    else:
                        factor_value = Decimal('0.00250')
                    factor_unit_match = "tCO2e/L"
                    anomalies_list.append("Default Scope 1 emission factor applied (no exact matching database record found).")
            else:
                # General procurement (Scope 3, Category 1)
                scope = 3
                category = "Procurement"
                # Map based on description keywords
                if 'office' in desc_lower or 'buro' in desc_lower:
                    activity_type = "Office Supplies"
                elif 'it' in desc_lower or 'hardware' in desc_lower or 'computer' in desc_lower:
                    activity_type = "IT Hardware"
                elif 'consult' in desc_lower or 'service' in desc_lower or 'dienst' in desc_lower:
                    activity_type = "Professional Services"
                else:
                    activity_type = "General Purchase Goods"
                
                # Convert amount to USD for Spend-based emission factors (tCO2e/USD)
                exch_rate = EXCHANGE_RATES.get(currency, Decimal('1.00'))
                amount_usd = amount * exch_rate
                
                normalized_qty = amount_usd
                norm_unit = "USD"
                
                # Fetch Spend emission factor
                ef = EmissionFactor.objects.filter(
                    scope=3,
                    category=category,
                    activity_type=activity_type,
                    year=(parsed_date.year if parsed_date else 2025)
                ).first()
                if ef:
                    factor_value = ef.factor_value
                    factor_unit_match = ef.factor_unit
                else:
                    # Defaults (tCO2e / USD, e.g. 0.0003 tCO2e = 300g CO2e per dollar)
                    if activity_type == "IT Hardware":
                        factor_value = Decimal('0.000320')
                    elif activity_type == "Office Supplies":
                        factor_value = Decimal('0.000180')
                    elif activity_type == "Professional Services":
                        factor_value = Decimal('0.000070')
                    else:
                        factor_value = Decimal('0.000150')
                    factor_unit_match = "tCO2e/USD"
                    anomalies_list.append("Default Spend-based Scope 3 emission factor applied.")

        # Calc emissions
        emissions = Decimal('0')
        if not is_failed:
            emissions = normalized_qty * factor_value
            if is_suspicious:
                record_status = 'SUSPICIOUS'

        anomalies_text = "; ".join(anomalies_list) if anomalies_list else ""
        
        # Create record (even if failed, so analysts can see the parsing failure and correct it)
        rec = NormalizedRecord.objects.create(
            organization=organization,
            raw_source=raw_source,
            facility=facility,
            scope=scope,
            category=category,
            activity_type=activity_type,
            activity_date=parsed_date or timezone.now().date(),
            original_quantity=qty,
            original_unit=orig_unit,
            normalized_quantity=normalized_qty,
            normalized_unit=norm_unit,
            emission_factor_value=factor_value,
            emission_factor_unit=factor_unit_match,
            emissions_tco2e=emissions,
            status=record_status,
            anomalies=anomalies_text,
            is_locked=False,
            comments=""
        )
        
        # Audit trail for ingestion
        AuditLog.objects.create(
            organization=organization,
            record=rec,
            action='INGEST',
            new_values={
                'scope': scope,
                'category': category,
                'activity_type': activity_type,
                'activity_date': str(rec.activity_date),
                'original_quantity': str(qty),
                'original_unit': orig_unit,
                'normalized_quantity': str(normalized_qty),
                'normalized_unit': norm_unit,
                'emissions_tco2e': str(emissions),
                'status': record_status,
                'anomalies': anomalies_text,
            }
        )
        
        if is_failed:
            failed_records_count += 1
        else:
            created_records_count += 1
            
    # Save parse statistics back to raw source
    raw_source.processing_logs = (
        f"Parsed SAP file. Created records: {created_records_count}. "
        f"Failed parsing lines: {failed_records_count}.\n"
        + "\n".join(logs)
    )
    if failed_records_count > 0 and created_records_count > 0:
        raw_source.status = 'PARTIAL'
    elif failed_records_count > 0:
        raw_source.status = 'FAILED'
    else:
        raw_source.status = 'SUCCESS'
    raw_source.save()
