import json
import math
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from ingestion.models import NormalizedRecord, IataAirport, EmissionFactor, AuditLog

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on the Earth
    in kilometers using the Haversine formula.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371.0 # Radius of earth in kilometers
    return c * r

def parse_travel_export(raw_source):
    """
    Parses a Corporate Travel JSON API payload.
    Example payload shape:
    [
      {
        "trip_id": "T-001",
        "employee_id": "E-101",
        "booking_date": "2025-11-01",
        "segments": [
          {
            "type": "flight",
            "origin": "SFO",
            "destination": "JFK",
            "cabin_class": "business",
            "distance_km": null
          },
          {
            "type": "hotel",
            "city": "New York",
            "country": "US",
            "room_nights": 4
          },
          {
            "type": "ground",
            "transport_type": "taxi",
            "distance_km": 18.5,
            "spend_usd": 65.00
          }
        ]
      }
    ]
    """
    organization = raw_source.organization
    payload = raw_source.raw_payload
    logs = []
    
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raw_source.status = 'FAILED'
        raw_source.processing_logs = f"JSON syntax error: {str(e)}"
        raw_source.save()
        return

    if not isinstance(data, list):
        # Allow single object wrap
        if isinstance(data, dict):
            data = [data]
        else:
            raw_source.status = 'FAILED'
            raw_source.processing_logs = "Root element of travel payload must be a JSON array or object."
            raw_source.save()
            return

    created_records_count = 0
    failed_records_count = 0
    
    for trip_idx, trip in enumerate(data, start=1):
        trip_id = trip.get('trip_id', f"TRIP-MOCK-{trip_idx}")
        booking_date_str = trip.get('booking_date', '')
        
        # Parse booking date
        parsed_date = None
        try:
            parsed_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            parsed_date = timezone.now().date()
            
        segments = trip.get('segments', [])
        if not segments:
            logs.append(f"Trip {trip_id} has no segments.")
            continue
            
        for seg_idx, seg in enumerate(segments, start=1):
            seg_type = seg.get('type', '').lower()
            anomalies_list = []
            is_failed = False
            is_suspicious = False
            
            scope = 3
            category = "Business Travel"
            activity_type = "Business Travel (General)"
            
            orig_qty = Decimal('0')
            orig_unit = ""
            norm_qty = Decimal('0')
            norm_unit = ""
            
            factor_value = Decimal('0.000000')
            factor_unit = "tCO2e"
            emissions = Decimal('0.000000')
            
            comments_parts = [f"Trip ID: {trip_id}", f"Segment: {seg_type}"]
            
            # --- Segment 1: FLIGHT ---
            if seg_type == 'flight':
                category = "Business Travel - Flights"
                origin = seg.get('origin', '').upper().strip()
                destination = seg.get('destination', '').upper().strip()
                cabin = seg.get('cabin_class', 'economy').lower().strip()
                dist_km = seg.get('distance_km')
                
                comments_parts.append(f"Routing: {origin}->{destination}")
                comments_parts.append(f"Cabin: {cabin}")
                
                # Check distances
                calculated_distance = False
                if dist_km is None:
                    # Lookup airport coordinates
                    ap_origin = IataAirport.objects.filter(iata_code=origin).first()
                    ap_dest = IataAirport.objects.filter(iata_code=destination).first()
                    
                    if ap_origin and ap_dest:
                        dist_km = haversine_distance(
                            ap_origin.latitude, ap_origin.longitude,
                            ap_dest.latitude, ap_dest.longitude
                        )
                        calculated_distance = True
                        comments_parts.append(f"Distance calculated via coordinates: {dist_km:.1f} km")
                    else:
                        is_failed = True
                        anomalies_list.append(f"Airport codes not found in airport coordinate lookup: origin='{origin}', dest='{destination}'")
                        dist_km = 0
                else:
                    try:
                        dist_km = float(dist_km)
                    except (ValueError, TypeError):
                        is_failed = True
                        anomalies_list.append(f"Invalid distance value '{dist_km}'")
                        dist_km = 0
                
                if not is_failed:
                    orig_qty = Decimal(str(dist_km))
                    orig_unit = "km"
                    norm_qty = orig_qty
                    norm_unit = "passenger-km"
                    
                    # Haul classification
                    # Short Haul: < 500km, Medium: 500km-3700km, Long: > 3700km
                    haul_length = "Medium Haul"
                    if dist_km < 500:
                        haul_length = "Short Haul"
                    elif dist_km > 3700:
                        haul_length = "Long Haul"
                        
                    activity_type = f"Flight - {haul_length} ({cabin.capitalize()})"
                    
                    # Query flight emission factor
                    ef = EmissionFactor.objects.filter(
                        scope=3,
                        category=category,
                        activity_type=activity_type
                    ).first()
                    
                    if ef:
                        factor_value = ef.factor_value
                        factor_unit = ef.factor_unit
                    else:
                        # Fallback defaults (tCO2e per passenger-km)
                        # Economy: ~0.00015, Business: ~0.00029, First: ~0.00045 (haul and cabin adjusted)
                        base_factor = Decimal('0.00015')
                        if cabin == 'business':
                            base_factor = Decimal('0.00029')
                        elif cabin == 'first':
                            base_factor = Decimal('0.00045')
                        
                        # Short haul has higher relative landing/takeoff cost per km
                        if haul_length == "Short Haul":
                            base_factor *= Decimal('1.2')
                            
                        factor_value = base_factor
                        factor_unit = "tCO2e/passenger-km"
                        anomalies_list.append("Default flight factor applied based on haul and class.")
            
            # --- Segment 2: HOTEL ---
            elif seg_type == 'hotel':
                category = "Business Travel - Hotels"
                city = seg.get('city', '')
                country = seg.get('country', '').upper().strip()
                nights = seg.get('room_nights')
                
                comments_parts.append(f"Hotel in: {city}, {country}")
                
                try:
                    nights_val = int(nights)
                    if nights_val <= 0:
                        is_suspicious = True
                        anomalies_list.append("Hotel room nights is zero or negative.")
                except (ValueError, TypeError):
                    is_failed = True
                    anomalies_list.append(f"Invalid room nights count '{nights}'")
                    nights_val = 0
                    
                if not is_failed:
                    orig_qty = Decimal(str(nights_val))
                    orig_unit = "room-nights"
                    norm_qty = orig_qty
                    norm_unit = "room-nights"
                    activity_type = f"Hotel Stay - {country}"
                    
                    # Query emission factors
                    ef = EmissionFactor.objects.filter(
                        scope=3,
                        category=category,
                        activity_type=activity_type
                    ).first()
                    
                    if not ef:
                        # Fallback search by category and country prefix
                        ef = EmissionFactor.objects.filter(
                            scope=3,
                            category=category,
                            activity_type__contains=country
                        ).first()
                        
                    if ef:
                        factor_value = ef.factor_value
                        factor_unit = ef.factor_unit
                    else:
                        # Fallbacks per room-night (tCO2e / room-night)
                        # US/Germany: ~0.020, general global: ~0.015
                        if country in ('US', 'USA'):
                            factor_value = Decimal('0.020400')
                        elif country in ('DE', 'GER'):
                            factor_value = Decimal('0.016500')
                        else:
                            factor_value = Decimal('0.018000')
                        factor_unit = "tCO2e/room-night"
                        anomalies_list.append("Default country hotel factor applied.")
            
            # --- Segment 3: GROUND ---
            elif seg_type == 'ground':
                category = "Business Travel - Ground"
                trans_type = seg.get('transport_type', 'taxi').lower().strip()
                dist_km = seg.get('distance_km')
                spend = seg.get('spend_usd')
                
                comments_parts.append(f"Type: {trans_type}")
                
                # Check if we use distance-based or spend-based calculations
                has_distance = False
                if dist_km is not None:
                    try:
                        dist_val = Decimal(str(dist_km))
                        if dist_val > 0:
                            has_distance = True
                            orig_qty = dist_val
                            orig_unit = "km"
                            norm_qty = dist_val
                            norm_unit = "passenger-km"
                            activity_type = f"Ground - {trans_type.capitalize()} (Distance)"
                    except (ValueError, TypeError):
                        anomalies_list.append(f"Invalid distance '{dist_km}' for ground travel, checking spend.")
                
                if not has_distance:
                    # Try spend-based EEIO fallback
                    if spend is not None:
                        try:
                            spend_val = Decimal(str(spend))
                            if spend_val > 0:
                                orig_qty = spend_val
                                orig_unit = "USD"
                                norm_qty = spend_val
                                norm_unit = "USD"
                                activity_type = f"Ground - {trans_type.capitalize()} (Spend)"
                                comments_parts.append(f"Spend-based calculation used: ${spend_val}")
                            else:
                                is_failed = True
                                anomalies_list.append("Both ground distance and spend are zero or negative.")
                        except (ValueError, TypeError):
                            is_failed = True
                            anomalies_list.append(f"Invalid spend '{spend}' and missing distance.")
                    else:
                        is_failed = True
                        anomalies_list.append("Missing both distance_km and spend_usd for ground travel.")
                        
                if not is_failed:
                    # Query factor database
                    ef = EmissionFactor.objects.filter(
                        scope=3,
                        category=category,
                        activity_type=activity_type
                    ).first()
                    
                    if ef:
                        factor_value = ef.factor_value
                        factor_unit = ef.factor_unit
                    else:
                        # Fallbacks
                        if norm_unit == "passenger-km":
                            # Distance factors (tCO2e / km)
                            if 'rail' in trans_type or 'train' in trans_type:
                                factor_value = Decimal('0.000041') # Train ~41g/km
                            elif 'taxi' in trans_type or 'uber' in trans_type:
                                factor_value = Decimal('0.000185') # Taxi ~185g/km
                            else:
                                factor_value = Decimal('0.000170') # Car rental avg ~170g/km
                            factor_unit = "tCO2e/passenger-km"
                            anomalies_list.append("Default ground distance-based factor applied.")
                        else:
                            # Spend factors (EEIO, tCO2e / USD)
                            if 'rail' in trans_type or 'train' in trans_type:
                                factor_value = Decimal('0.000120')
                            elif 'taxi' in trans_type or 'uber' in trans_type:
                                factor_value = Decimal('0.000280')
                            else:
                                factor_value = Decimal('0.000220')
                            factor_unit = "tCO2e/USD"
                            anomalies_list.append("Default ground spend-based (EEIO) factor applied.")
            
            else:
                is_failed = True
                anomalies_list.append(f"Unknown segment type '{seg_type}'")

            # --- Final Record Save ---
            if is_failed:
                record_status = 'FAILED'
                emissions = Decimal('0.000000')
            else:
                emissions = norm_qty * factor_value
                record_status = 'SUSPICIOUS' if is_suspicious else 'PENDING_REVIEW'
                
            anomalies_text = "; ".join(anomalies_list) if anomalies_list else ""
            
            rec = NormalizedRecord.objects.create(
                organization=organization,
                raw_source=raw_source,
                facility=None,  # Corporate travel usually not tied directly to a single facility
                scope=scope,
                category=category,
                activity_type=activity_type,
                activity_date=parsed_date,
                original_quantity=orig_qty,
                original_unit=orig_unit,
                normalized_quantity=norm_qty,
                normalized_unit=norm_unit,
                emission_factor_value=factor_value,
                emission_factor_unit=factor_unit,
                emissions_tco2e=emissions,
                status=record_status,
                anomalies=anomalies_text,
                is_locked=False,
                comments=" | ".join(comments_parts)
            )
            
            # Audit log
            AuditLog.objects.create(
                organization=organization,
                record=rec,
                action='INGEST',
                new_values={
                    'scope': scope,
                    'category': category,
                    'activity_date': str(parsed_date),
                    'original_quantity': str(orig_qty),
                    'original_unit': orig_unit,
                    'normalized_quantity': str(norm_qty),
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
                
    # Update logs
    raw_source.processing_logs = (
        f"Parsed Travel JSON API payload. Created records: {created_records_count}. "
        f"Failed segments: {failed_records_count}."
    )
    if failed_records_count > 0 and created_records_count > 0:
        raw_source.status = 'PARTIAL'
    elif failed_records_count > 0:
        raw_source.status = 'FAILED'
    else:
        raw_source.status = 'SUCCESS'
    raw_source.save()
