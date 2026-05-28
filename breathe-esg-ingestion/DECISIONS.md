# Architectural & Product Decisions (DECISIONS.md)

This log summarizes the ambiguities resolved during development, the specific subsets of data we implemented, and the list of design questions for the Product Manager.

---

## 1. Ambiguities Resolved

### 1.1 Inconsistent Ingestion Dates & Time Zones
* **Ambiguity**: Client files can contain dates in varying formats (e.g. European `DD.MM.YYYY` from SAP, American `MM/DD/YYYY` from Utilities, and ISO `YYYY-MM-DD` from APIs).
* **Decision**: We implemented an adaptive date parsing utility in all three parsers that iterates through a tuple of date formats (`%d.%m.%Y`, `%Y-%m-%d`, `%m/%d/%Y`). If all format checks fail, the system does not crash; instead, it marks the record as `FAILED`, outputs a validation error message in the anomalies column, and saves the record so it can be corrected in the UI.

### 1.2 Multi-Currency Normalization
* **Ambiguity**: SAP procurement documents are recorded in local document currencies (EUR, GBP, USD), but spend-based emissions factors (EEIO) are denominated in tonnes CO2e per dollar ($).
* **Decision**: We introduced a static exchange rate registry in the backend parser (`EXCHANGE_RATES`). All spend amounts are converted to USD before the Scope 3 category emission factors are applied.

### 1.3 Missing Flight Distance Metrics
* **Ambiguity**: Travel agencies often supply flight records showing only Departure/Arrival airport IATA codes (e.g., `SFO -> JFK`) without mileage or kilometers.
* **Decision**: We integrated a spatial database of major international airports (`IataAirport` table) containing latitude and longitude. The backend computes the Great Circle distance using the Haversine formula dynamically when the distance is omitted in the payload.

---

## 2. Ingestion Boundaries (What is Handled vs. Ignored)

### 2.1 SAP Data Stream
* **Mode Selected**: Pipe-delimited flat-file CSV/TXT export (similar to reports downloaded via transactions `AL11` or `FBL3N`).
* **Justification**: Flat files are the most common batch-transfer mode used by IT teams to deliver ERP data without building expensive, high-governance API integrations.
* **Handled**: Column header translation from standard German SAP parameters (`BUDAT`, `MENGE`, `MEINS`, `WERKS`, `DMBTR`, `WAERS`), basic fuel stationary combustion mapping (Scope 1), and general procurement mapping (Scope 3 Category 1).
* **Ignored**: IDocs (Intermediate Documents) and SOAP BAPI connections. These require enterprise message queues and middleware (such as SAP Process Integration or MuleSoft) which are outside the scope of a 4-day prototype.

### 2.2 Utility Data Stream
* **Mode Selected**: Utility Portal CSV Export.
* **Justification**: Facilities teams typically download bills as spreadsheets from portals (e.g., PG&E or ConEd billing history dashboards).
* **Handled**: Irregular billing periods (pro-rated day-by-day), meter-to-facility mapping, and eGRID subregion-specific electricity emissions factors.
* **Ignored**: PDF scraping of bills. PDF scraping (e.g. using OCR tools like AWS Textract) is highly fragile, subject to layout changes by utilities, and is best handled by third-party utility APIs (like Urjanet) in production.

### 2.3 Corporate Travel Data Stream
* **Mode Selected**: JSON API Payload.
* **Justification**: Travel platforms (e.g., Navan, Concur) typically communicate travel segments through structured REST APIs.
* **Handled**: Flight segments (with haul classification and cabin class adjustment), Hotel lodging (by room night and country-specific factors), and Ground transport (taxis, rail, rental cars) with a spend-based EEIO fallback if distance is missing.
* **Ignored**: Complex multi-leg trips with mixed modes (e.g. taxi -> train -> flight in one line). We assume the API splits trips into individual, distinct segments.

---

## 3. Product Manager Questions

If we could align with the Product Manager today, we would clarify:
1. **Facility Mapping Registry**: Where is the master record of meter numbers to facility codes maintained? Should Breathe ESG expose an admin dashboard to let clients configure these associations, or is it managed via backend DB migrations?
2. **Dynamic FX Rates**: Do we need to integrate with an external financial service (e.g., Open Exchange Rates API) to fetch historical exchange rates active on the *posting date* of the SAP record, or is a monthly static rate sufficient?
3. **Auditor Locking Protocol**: Once an analyst approves a record, it becomes locked (`is_locked=True`). Can an Administrator override this lock if an auditor requests a correction, or does it require an official amendment record?
4. **Grid Intensity Variance**: For pro-rated utility data, does the auditor expect carbon calculations using the factor active on the *billing end date*, or should we apply factors based on the specific calendar year of the daily slice? (We currently apply it by the slice date).
