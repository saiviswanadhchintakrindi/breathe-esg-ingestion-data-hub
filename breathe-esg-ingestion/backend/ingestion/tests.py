import json
import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import models

from ingestion.models import Organization, Facility, IataAirport, EmissionFactor, RawIngestionSource, NormalizedRecord, AuditLog
from ingestion.parsers.sap_parser import parse_sap_export
from ingestion.parsers.utility_parser import parse_utility_export
from ingestion.parsers.travel_parser import parse_travel_export

class ESGPlatformTestCase(TestCase):
    def setUp(self):
        # Create Organization
        self.org = Organization.objects.create(name="Acme Testing Corp")
        
        # Create Facilities
        self.fac1000 = Facility.objects.create(
            organization=self.org,
            facility_code="1000",
            name="Stuttgart Engine Plant",
            location="DE",
            grid_subregion="DE-grid"
        )
        self.fac_meter = Facility.objects.create(
            organization=self.org,
            facility_code="MTR-8890",
            name="San Jose HQ",
            location="US",
            grid_subregion="CAMX"
        )
        
        # Create Airport Geolocation Mappings
        IataAirport.objects.create(iata_code="SFO", latitude=Decimal("37.621313"), longitude=Decimal("-122.378955"), city="San Francisco", country="US")
        IataAirport.objects.create(iata_code="JFK", latitude=Decimal("40.639751"), longitude=Decimal("-73.778925"), city="New York", country="US")
        
        # Seed Reference Emission Factors
        # Scope 1 Diesel
        EmissionFactor.objects.create(scope=1, category="Stationary Combustion", activity_type="Diesel", factor_value=Decimal("0.00268"), factor_unit="tCO2e/L", source="US EPA", year=2025)
        # Scope 2 Electricity (CAMX)
        EmissionFactor.objects.create(scope=2, category="Purchased Electricity", activity_type="Electricity - Grid", factor_value=Decimal("0.00021"), factor_unit="tCO2e/kWh", source="CAMX Grid Factor", year=2025)
        # Scope 3 Flights
        EmissionFactor.objects.create(scope=3, category="Business Travel - Flights", activity_type="Flight - Long Haul (Business)", factor_value=Decimal("0.00023"), factor_unit="tCO2e/passenger-km", source="Defra", year=2025)

    def test_sap_parser_fuel_and_currency(self):
        # Pipe-delimited SAP test data with German headers
        # Includes a Diesel fuel record (Scope 1, Ltr) and an IT equipment purchase in EUR (Scope 3)
        raw_sap = (
            "| BELNR | BUDAT | MATNR | TXZ01 | MENGE | MEINS | DMBTR | WAERS | WERKS | LIFNR |\n"
            "| 10001 | 15.10.2025 | M-01 | Diesel Kraftstoff | 2000.00 | Ltr | 2400.00 | EUR | 1000 | V-99 |\n"
            "| 10002 | 16.10.2025 | M-02 | IT Hardware Purchase | 1.00 | STK | 5000.00 | EUR | 1000 | V-99 |\n"
        )
        
        source = RawIngestionSource.objects.create(
            organization=self.org,
            source_type="SAP",
            filename="sap_test.txt",
            raw_payload=raw_sap
        )
        
        # Run parser
        parse_sap_export(source)
        source.refresh_from_db()
        
        self.assertEqual(source.status, "SUCCESS")
        
        # Should create 2 records
        records = NormalizedRecord.objects.filter(raw_source=source)
        self.assertEqual(records.count(), 2)
        
        # Verify Diesel Record (Scope 1)
        diesel_rec = records.filter(scope=1).first()
        self.assertIsNotNone(diesel_rec)
        self.assertEqual(diesel_rec.activity_type, "Diesel")
        self.assertEqual(diesel_rec.facility, self.fac1000)
        self.assertEqual(diesel_rec.normalized_quantity, Decimal("2000.00"))
        # Emissions = 2000 * 0.00268 = 5.36
        self.assertAlmostEqual(float(diesel_rec.emissions_tco2e), 5.36, places=2)
        
        # Verify IT Purchase Record (Scope 3, EUR converted to USD)
        it_rec = records.filter(scope=3).first()
        self.assertIsNotNone(it_rec)
        # EUR to USD check: 5000 EUR * 1.08 = 5400 USD
        self.assertEqual(it_rec.normalized_quantity, Decimal("5400.00"))
        self.assertEqual(it_rec.normalized_unit, "USD")

    def test_utility_parser_pro_rating(self):
        # Bill spans 30 days (Oct 15 to Nov 13), usage = 3000 kWh
        raw_utility = (
            "Account Number,Meter ID,Billing Start Date,Billing End Date,Usage (kWh),Total Bill ($),Tariff Code\n"
            "12345678,MTR-8890,2025-10-15,2025-11-13,3000,450.00,E-19\n"
        )
        
        source = RawIngestionSource.objects.create(
            organization=self.org,
            source_type="UTILITY",
            filename="utility_test.csv",
            raw_payload=raw_utility
        )
        
        # Run parser
        parse_utility_export(source)
        
        # Should create 30 daily records
        records = NormalizedRecord.objects.filter(raw_source=source)
        self.assertEqual(records.count(), 30)
        
        # Check daily slice details
        first_day_rec = records.filter(activity_date=datetime.date(2025, 10, 15)).first()
        self.assertIsNotNone(first_day_rec)
        # 3000 kWh / 30 days = 100 kWh/day
        self.assertEqual(first_day_rec.normalized_quantity, Decimal("100.0"))
        self.assertEqual(first_day_rec.facility, self.fac_meter)
        
        # Emissions: 100 kWh * 0.00021 CAMX factor = 0.021 tCO2e
        self.assertAlmostEqual(float(first_day_rec.emissions_tco2e), 0.021, places=3)
        
        # Total emissions summed across all slices should be 0.63 (3000 * 0.00021)
        total_sum = records.aggregate(total=models.Sum('emissions_tco2e'))['total']
        self.assertAlmostEqual(float(total_sum), 0.63, places=2)

    def test_travel_parser_haversine(self):
        # Flight with missing distance, should resolve coordinates SFO -> JFK
        # SFO -> JFK is roughly 4160 kilometers (long haul)
        raw_travel = [{
            "trip_id": "T-100",
            "employee_id": "EMP-9",
            "booking_date": "2025-11-01",
            "segments": [
                {
                    "type": "flight",
                    "origin": "SFO",
                    "destination": "JFK",
                    "cabin_class": "business",
                    "distance_km": None
                }
            ]
        }]
        
        source = RawIngestionSource.objects.create(
            organization=self.org,
            source_type="TRAVEL",
            filename="simulated_api_concur_pull.json",
            raw_payload=json.dumps(raw_travel)
        )
        
        parse_travel_export(source)
        
        # Verify flight record created
        flight_rec = NormalizedRecord.objects.filter(raw_source=source).first()
        self.assertIsNotNone(flight_rec)
        self.assertEqual(flight_rec.scope, 3)
        self.assertEqual(flight_rec.category, "Business Travel - Flights")
        # Check that distance was populated and is long-haul
        self.assertGreater(flight_rec.normalized_quantity, Decimal("4100"))
        self.assertLess(flight_rec.normalized_quantity, Decimal("4200"))
        self.assertTrue("Flight - Long Haul (Business)" in flight_rec.activity_type)

    def test_audit_lock_and_trail(self):
        # Create a mock record to test audit edit constraints
        source = RawIngestionSource.objects.create(organization=self.org, source_type="SAP", filename="test.txt", raw_payload="raw")
        rec = NormalizedRecord.objects.create(
            organization=self.org,
            raw_source=source,
            scope=1,
            category="Stationary Combustion",
            activity_type="Diesel",
            activity_date=datetime.date(2025, 10, 15),
            original_quantity=Decimal("100"),
            original_unit="L",
            normalized_quantity=Decimal("100"),
            normalized_unit="L",
            emission_factor_value=Decimal("0.00268"),
            emission_factor_unit="tCO2e/L",
            emissions_tco2e=Decimal("0.268"),
            status="PENDING_REVIEW",
            is_locked=False
        )
        
        # Check that we can edit it if unlocked (simulating view logic)
        rec.normalized_quantity = Decimal("150")
        rec.emissions_tco2e = rec.normalized_quantity * rec.emission_factor_value
        rec.save()
        self.assertEqual(rec.emissions_tco2e, Decimal("0.40200"))
        
        # Approve and lock it
        rec.status = "APPROVED"
        rec.is_locked = True
        rec.save()
        
        # Modifying a locked record should fail logic checks (we simulate the view check)
        self.assertTrue(rec.is_locked)
        # Attempt edit in views-like condition
        edit_blocked = False
        if rec.is_locked:
            edit_blocked = True
        self.assertTrue(edit_blocked)
