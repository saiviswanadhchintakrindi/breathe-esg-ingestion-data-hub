# Real-World Data Sources (SOURCES.md)

This document outlines the real-world source formats we researched, what we learned from their structures, how our mock datasets represent them, and what would fail in a production environment.

---

## 1. SAP ERP: Fuel and Procurement Data

### 1.1 Research & Format Realities
Enterprise resource planning (ERP) exports from SAP are rarely standard CSVs. They are often pipe-separated, custom-delimited, or fixed-width text files extracted from transactions like `AL11` (SAP Directories) or custom ABAP queries pulling from database tables:
- **`BSEG`**: Accounting Document Segment (stores posting dates `BUDAT` and transaction currencies `WAERS`).
- **`EKPO`**: Purchasing Document Item (stores PO quantities `MENGE` and units `MEINS`).
- **`MAKT`**: Material Descriptions (stores descriptions `MAKTX` or short texts `TXZ01`).
Column headers are frequently left in German (e.g., `WERKS` for plant, `MANDT` for client client code, `LIFNR` for vendor).

### 1.2 What We Learned
- **Decimals & Thousands**: SAP uses European number formatting by default (e.g., `5.000,00` instead of `5000.00`).
- **Plant Codes**: Fuel orders are coded to internal plants (`WERKS`, e.g., `1000`) rather than physical office names.
- **Unit Codes**: SAP uses custom unit strings (e.g., `Ltr` for Liters, `TO` for Tonnes, `ST` or `STK` for Stück/pieces).

### 1.3 How to Reproduce & Deploy
Our sample file [sap_export_raw.txt](file:///C:/Users/DELL/.gemini/antigravity/scratch/breathe-esg-ingestion/sample_data/sap_export_raw.txt) mimics this:
```txt
| BELNR | BUDAT | MATNR | TXZ01 | MENGE | MEINS | DMBTR | WAERS | WERKS | LIFNR |
| 100021 | 12.10.2025 | M-102 | Fuel Oil (Heizöl) | 4500.00 | Ltr | 5850.00 | EUR | 1000 | VEND-998 |
```
- **Real-World Failures**:
  - SAP represents credit adjustments or returns by placing a negative sign at the *end* of the number (e.g., `1500.00-`). A standard parser (like Python's `Decimal` constructor) will crash on this unless normalized first.
  - Multi-line descriptions that contain actual pipe characters `|` will break raw splits unless parsed with a formal CSV engine utilizing escaping.

---

## 2. Utility Data: Purchased Electricity

### 2.1 Research & Format Realities
Facilities teams retrieve electricity data from utility portals (such as PG&E, National Grid, or ConEd). They download:
1. **Green Button XML/JSON data**: Structured energy usage logs.
2. **Billing History CSVs**: Downloaded tables of monthly billing variables.
We implemented the billing CSV export because facilities teams frequently maintain these files manually or export them directly to check cost metrics.

### 2.2 What We Learned
- **Irrregular Cycles**: Billing periods do not span neat calendar months (e.g., Oct 15 to Nov 13).
- **Tariff Codes**: Energy usage is tied to tariff structures (e.g., PG&E's `E-19` or industrial rates).
- **Multiple Meters**: A single facility can operate dozens of smart meters.

### 2.3 How to Reproduce & Deploy
Our sample file [utility_portal_raw.csv](file:///C:/Users/DELL/.gemini/antigravity/scratch/breathe-esg-ingestion/sample_data/utility_portal_raw.csv) maps these behaviors:
```csv
Account Number,Meter ID,Billing Start Date,Billing End Date,Usage (kWh),Total Bill ($),Tariff Code
12345678,MTR-8890,2025-10-15,2025-11-13,6000,900.00,E-19
```
- **Real-World Failures**:
  - **Billing Overlaps/Gaps**: A utility might issue an adjusted bill covering an overlapping date range, or a meter swap might leave a 3-day gap with no readings.
  - **Net Metering**: Facilities with solar arrays might feed electricity back into the grid, returning negative monthly usage. A naive check flagging all negatives as errors will fail on net-metered buildings.

---

## 3. Corporate Travel: Flights, Hotels, Ground Transport

### 3.1 Research & Format Realities
Travel booking systems like Concur, Navan, or Egencia expose travel records via JSON APIs. Our parser ingests a nested structure containing trip headers, booking parameters, and booking segments (flights, lodging, ground).

### 3.2 What We Learned
- **Missing Distance**: Distance metrics are frequently missing. Platforms only return airport IATA origin/destination codes.
- **Cabin Classes**: Cabin codes (Economy vs. Business) dramatically affect carbon emission factors due to seat footprint sizes.
- **Spend fallbacks**: Ground travel (Uber/Taxi) lacks mileage. We must fall back to spend-based Environmentally Extended Input-Output (EEIO) factors.

### 3.3 How to Reproduce & Deploy
Our sample file [travel_concur_raw.json](file:///C:/Users/DELL/.gemini/antigravity/scratch/breathe-esg-ingestion/sample_data/travel_concur_raw.json) covers this:
```json
{
  "trip_id": "TRIP-2025-001",
  "segments": [
    { "type": "flight", "origin": "SFO", "destination": "JFK", "cabin_class": "business" }
  ]
}
```
- **Real-World Failures**:
  - **Airport Code Changes**: New airports or regional charters might use IATA codes not yet in our database, causing coordinate lookups to fail.
  - **Multi-Destination Hotel Stays**: A Concur receipt might list check-ins for multi-day stays, but the traveler split their stay across regions.
  - **Currency Variances**: Traveling employees submit expenses in local currencies (such as CAD, SGD). If the platform passes non-USD currencies without mapping them, spend-based calculations will apply USD factors to inflated values.
