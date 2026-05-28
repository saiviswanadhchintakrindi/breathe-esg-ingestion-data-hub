import os
import json

# Setup directory
os.makedirs('sample_data', exist_ok=True)

# 1. Generate SAP Procurement & Fuel Flat File (Pipe-separated German)
sap_content = """| BELNR | BUDAT | MATNR | TXZ01 | MENGE | MEINS | DMBTR | WAERS | WERKS | LIFNR |
| 100021 | 12.10.2025 | M-102 | Fuel Oil (Heizöl) | 4500.00 | Ltr | 5850.00 | EUR | 1000 | VEND-998 |
| 100022 | 15.10.2025 | M-201 | IT Server Equipment | 3.00 | St | 12500.00 | USD | 1100 | VEND-501 |
| 100023 | 20.10.2025 | M-101 | Diesel Kraftstoff | 2000.00 | Ltr | 2400.00 | EUR | 1000 | VEND-998 |
| 100024 | 22.10.2025 | M-503 | Consulting Services | 1.00 | Stk | 15000.00 | EUR | 1000 | VEND-221 |
| 100025 | 24.10.2025 | M-101 | Diesel Kraftstoff | -500.00 | Ltr | -600.00 | EUR | 1000 | VEND-998 |
| 100026 | 28.10.2025 | M-101 | Diesel Kraftstoff | 1500.00 | Ltr | 1800.00 | EUR | 9999 | VEND-998 |
| 100027 | 32.10.2025 | M-101 | Diesel Kraftstoff | 800.00 | Ltr | 960.00 | EUR | 1100 | VEND-998 |
| 100028 | 01.11.2025 | M-404 | Office Printing Paper | 150.00 | kg | 450.00 | USD | 1100 | VEND-112 |
| 100029 | 05.11.2025 | M-102 | Fuel Oil (Heizöl) | 3.00 | to | 3300.00 | EUR | 1000 | VEND-998 |
"""

with open('sample_data/sap_export_raw.txt', 'w', encoding='utf-8') as f:
    f.write(sap_content.strip())
print("Generated sample_data/sap_export_raw.txt")

# 2. Generate Utility Portal Electricity Export (CSV)
utility_content = """Account Number,Meter ID,Billing Start Date,Billing End Date,Usage (kWh),Total Bill ($),Tariff Code
12345678,MTR-8890,2025-10-15,2025-11-13,6000,900.00,E-19
12345678,MTR-8890,2025-11-14,2025-12-14,7500,1125.00,E-19
87654321,MTR-1212,2025-10-01,2025-10-31,15500,2480.00,ERCOT-IND
87654321,MTR-1212,2025-11-01,2025-11-30,-200,0.00,ERCOT-IND
87654321,MTR-9999,2025-10-01,2025-10-31,1800,290.00,ERCOT-IND
12345678,MTR-8890,2025-05-01,2025-07-30,24000,3600.00,E-19
12345678,MTR-8890,2025-08-01,invalid_date,3500,500.00,E-19
"""

with open('sample_data/utility_portal_raw.csv', 'w', encoding='utf-8') as f:
    f.write(utility_content.strip())
print("Generated sample_data/utility_portal_raw.csv")

# 3. Generate Corporate Travel Concur JSON API payload (JSON)
travel_data = [
    {
        "trip_id": "TRIP-2025-001",
        "employee_id": "EMP-412",
        "booking_date": "2025-11-03",
        "segments": [
            {
                "type": "flight",
                "origin": "SFO",
                "destination": "JFK",
                "cabin_class": "business",
                "distance_km": None
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
                "distance_km": 24.5,
                "spend_usd": 75.00
            }
        ]
    },
    {
        "trip_id": "TRIP-2025-002",
        "employee_id": "EMP-881",
        "booking_date": "2025-11-10",
        "segments": [
            {
                "type": "flight",
                "origin": "LHR",
                "destination": "FRA",
                "cabin_class": "economy",
                "distance_km": None
            },
            {
                "type": "hotel",
                "city": "Frankfurt",
                "country": "DE",
                "room_nights": 2
            },
            {
                "type": "ground",
                "transport_type": "train",
                "distance_km": None,
                "spend_usd": 45.00
            }
        ]
    },
    {
        "trip_id": "TRIP-2025-003",
        "employee_id": "EMP-105",
        "booking_date": "2025-11-15",
        "segments": [
            {
                "type": "flight",
                "origin": "SFO",
                "destination": "FRA",
                "cabin_class": "first",
                "distance_km": 9150.0  # Explicitly provided
            },
            {
                "type": "hotel",
                "city": "Frankfurt",
                "country": "DE",
                "room_nights": 0  # Suspicious zero nights
            },
            {
                "type": "ground",
                "transport_type": "helicopter",
                "distance_km": None,
                "spend_usd": None  # Missing both metrics (will fail validation)
            }
        ]
    },
    {
        "trip_id": "TRIP-2025-004",
        "employee_id": "EMP-007",
        "booking_date": "2025-11-20",
        "segments": [
            {
                "type": "flight",
                "origin": "SFO",
                "destination": "XYZ",  # XYZ is an unknown airport, coordinate lookup fails
                "cabin_class": "economy",
                "distance_km": None
            }
        ]
    }
]

with open('sample_data/travel_concur_raw.json', 'w', encoding='utf-8') as f:
    json.dump(travel_data, f, indent=2)
print("Generated sample_data/travel_concur_raw.json")
