from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from ingestion.models import Organization, UserProfile, Facility, IataAirport, EmissionFactor

class Command(BaseCommand):
    help = "Seeds initial ESG reference database: Organization, Users, Facilities, Airports, and Emission Factors."

    def handle(self, *args, **options):
        self.stdout.write("Seeding ESG reference data...")

        # 1. Create Organization
        org, created = Organization.objects.get_or_create(name="Acme Global Industries")
        if created:
            self.stdout.write(f"Created Organization: {org.name}")
        else:
            self.stdout.write(f"Organization '{org.name}' already exists.")

        # 2. Create Users
        # Admin User
        admin_user, u_created = User.objects.get_or_create(
            username="admin",
            email="admin@acmeglobal.com"
        )
        if u_created:
            admin_user.set_password("admin123")
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.save()
            UserProfile.objects.create(user=admin_user, organization=org, role='ADMIN')
            self.stdout.write("Created Superuser: admin / admin123")
        
        # Analyst User
        analyst_user, u_created = User.objects.get_or_create(
            username="analyst",
            email="analyst@acmeglobal.com"
        )
        if u_created:
            analyst_user.set_password("analyst123")
            analyst_user.save()
            UserProfile.objects.create(user=analyst_user, organization=org, role='ANALYST')
            self.stdout.write("Created Analyst user: analyst / analyst123")

        # 3. Create Facilities (mapping plant codes and meter IDs)
        facilities_to_create = [
            {"code": "1000", "name": "Stuttgart Engine Plant", "loc": "DE", "grid": "DE-grid"},
            {"code": "1100", "name": "Munich Assembly Hub", "loc": "DE", "grid": "DE-grid"},
            {"code": "MTR-8890", "name": "San Jose R&D Offices", "loc": "US", "grid": "CAMX"},
            {"code": "MTR-1212", "name": "Austin Server Data Center", "loc": "US", "grid": "ERCOT"},
        ]
        for f in facilities_to_create:
            fac, f_created = Facility.objects.get_or_create(
                organization=org,
                facility_code=f["code"],
                defaults={
                    "name": f["name"],
                    "location": f["loc"],
                    "grid_subregion": f["grid"]
                }
            )
            if f_created:
                self.stdout.write(f"Created Facility: {fac.name} (Code: {fac.facility_code})")

        # 4. Seed Airports
        airports = [
            {"code": "SFO", "city": "San Francisco", "country": "US", "lat": 37.621313, "lon": -122.378955},
            {"code": "JFK", "city": "New York", "country": "US", "lat": 40.639751, "lon": -73.778925},
            {"code": "LHR", "city": "London", "country": "GB", "lat": 51.470022, "lon": -0.454295},
            {"code": "FRA", "city": "Frankfurt", "country": "DE", "lat": 50.037932, "lon": 8.562152},
            {"code": "CDG", "city": "Paris", "country": "FR", "lat": 49.009691, "lon": 2.547925},
            {"code": "SIN", "city": "Singapore", "country": "SG", "lat": 1.364420, "lon": 103.991012},
        ]
        for ap in airports:
            airport, ap_created = IataAirport.objects.get_or_create(
                iata_code=ap["code"],
                defaults={
                    "city": ap["city"],
                    "country": ap["country"],
                    "latitude": Decimal(str(ap["lat"])),
                    "longitude": Decimal(str(ap["lon"]))
                }
            )
            if ap_created:
                self.stdout.write(f"Created Airport: {airport.iata_code} ({airport.city})")

        # 5. Seed Emission Factors
        factors = [
            # Scope 1 - Stationary Combustion fuels (tCO2e per Liter)
            {"scope": 1, "cat": "Stationary Combustion", "type": "Diesel", "val": 0.00268, "unit": "tCO2e/L", "src": "US EPA GHGRP (2025)", "yr": 2025},
            {"scope": 1, "cat": "Stationary Combustion", "type": "Gasoline", "val": 0.00231, "unit": "tCO2e/L", "src": "US EPA GHGRP (2025)", "yr": 2025},
            {"scope": 1, "cat": "Stationary Combustion", "type": "Heating Oil", "val": 0.00252, "unit": "tCO2e/L", "src": "US EPA GHGRP (2025)", "yr": 2025},

            # Scope 2 - Purchased Electricity (tCO2e per kWh)
            {"scope": 2, "cat": "Purchased Electricity", "type": "Electricity - Grid", "val": 0.000210, "unit": "tCO2e/kWh", "src": "US EPA eGRID (CAMX California) 2025", "yr": 2025},
            {"scope": 2, "cat": "Purchased Electricity", "type": "Electricity - Grid", "val": 0.000355, "unit": "tCO2e/kWh", "src": "US EPA eGRID (ERCOT Texas) 2025", "yr": 2025},
            {"scope": 2, "cat": "Purchased Electricity", "type": "Electricity - Grid", "val": 0.000380, "unit": "tCO2e/kWh", "src": "Germany Federal Environment Agency (DE) 2025", "yr": 2025},
            {"scope": 2, "cat": "Purchased Electricity", "type": "Electricity - Grid", "val": 0.000385, "unit": "tCO2e/kWh", "src": "Global Average Grid Factor", "yr": 2025},

            # Scope 3 - Flights (tCO2e per passenger-km)
            {"scope": 3, "cat": "Business Travel - Flights", "type": "Flight - Short Haul (Economy)", "val": 0.000150, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Flights", "type": "Flight - Short Haul (Business)", "val": 0.000270, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Flights", "type": "Flight - Medium Haul (Economy)", "val": 0.000130, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Flights", "type": "Flight - Medium Haul (Business)", "val": 0.000250, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Flights", "type": "Flight - Long Haul (Economy)", "val": 0.000115, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Flights", "type": "Flight - Long Haul (Business)", "val": 0.000230, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},

            # Scope 3 - Hotels (tCO2e per room-night)
            {"scope": 3, "cat": "Business Travel - Hotels", "type": "Hotel Stay - US", "val": 0.020400, "unit": "tCO2e/room-night", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Hotels", "type": "Hotel Stay - DE", "val": 0.016500, "unit": "tCO2e/room-night", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Hotels", "type": "Hotel Stay - GB", "val": 0.014200, "unit": "tCO2e/room-night", "src": "UK Defra (2025)", "yr": 2025},

            # Scope 3 - Ground (Distance and Spend based)
            {"scope": 3, "cat": "Business Travel - Ground", "type": "Ground - Taxi (Distance)", "val": 0.000185, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Ground", "type": "Ground - Taxi (Spend)", "val": 0.000280, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Ground", "type": "Ground - Rail (Distance)", "val": 0.000041, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Ground", "type": "Ground - Rail (Spend)", "val": 0.000120, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Ground", "type": "Ground - Car Rental (Distance)", "val": 0.000170, "unit": "tCO2e/passenger-km", "src": "UK Defra (2025)", "yr": 2025},
            {"scope": 3, "cat": "Business Travel - Ground", "type": "Ground - Car Rental (Spend)", "val": 0.000220, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2025)", "yr": 2025},

            # Scope 3 - Supply Chain Procurement (tCO2e per USD spend)
            {"scope": 3, "cat": "Procurement", "type": "IT Hardware", "val": 0.000320, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2021)", "yr": 2025},
            {"scope": 3, "cat": "Procurement", "type": "Office Supplies", "val": 0.000180, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2021)", "yr": 2025},
            {"scope": 3, "cat": "Procurement", "type": "Professional Services", "val": 0.000070, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2021)", "yr": 2025},
            {"scope": 3, "cat": "Procurement", "type": "General Purchase Goods", "val": 0.000150, "unit": "tCO2e/USD", "src": "US EPA Supply Chain EEIO (2021)", "yr": 2025},
        ]

        for f in factors:
            factor, ef_created = EmissionFactor.objects.get_or_create(
                scope=f["scope"],
                category=f["cat"],
                activity_type=f["type"],
                year=f["yr"],
                defaults={
                    "factor_value": Decimal(str(f["val"])),
                    "factor_unit": f["unit"],
                    "source": f["src"]
                }
            )
            if ef_created:
                self.stdout.write(f"Created Emission Factor: {factor.category} - {factor.activity_type} ({factor.year})")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
