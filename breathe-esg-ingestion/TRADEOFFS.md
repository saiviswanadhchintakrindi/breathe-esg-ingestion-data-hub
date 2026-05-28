# Technical Tradeoffs (TRADEOFFS.md)

To deliver a high-quality, audit-ready prototype within 4 days, we deliberately deferred three engineering features. This document details the technical and product rationale behind these tradeoffs.

---

## 1. Deferring Celery/Redis Asynchronous Task Queues
* **What We Did**: File uploads and parsing runs are executed synchronously inside the Django request-response cycle (`IngestAPIView`).
* **Why We Did It**:
  - **Simplicity of Deployment**: Introducing Celery requires running a message broker (Redis or RabbitMQ) and maintaining worker processes. This increases deployment complexity and local machine runtime setup.
  - **Prototype Scale**: The files being tested contain under 1,000 rows. Processing completes in under 200ms, making asynchronous queues unnecessary for this phase.
* **Production Alternative**: In production, files may contain millions of purchase ledger records. Running them synchronously would trigger HTTP timeout errors. We would introduce a Celery queue where the API records the file upload, returns a task ID, and processes the file in the background, updating status via WebSockets.

---

## 2. Deferring OCR Utility Bill Scanning (PDF to Data)
* **What We Did**: We require utility electricity data to be uploaded as structured CSV exports.
* **Why We Did It**:
  - **High Maintenance Cost**: PDF layout engines differ across thousands of utility companies and frequently update. Writing robust custom parsers for PDF bills leads to fragile code.
  - **Aesthetic focus**: Writing PDF extractors would absorb 50% of the timeline, detracting from the core ledger audit functionality, multi-tenancy, and review screens.
* **Production Alternative**: In production, Breathe ESG should utilize Arcadia, Urjanet, or an OCR parsing microservice (like AWS Textract or Document AI) configured to parse PDF coordinates into structured data before delivering it to our API.

---

## 3. Deferring ML-based Outlier Anomaly Detection
* **What We Did**: We implemented rigid, explainable, rule-based anomaly triggers:
  - Negative values (quantity/spend).
  - Out-of-bounds billing periods (>45 days).
  - Missing lookups (facilities or airports).
* **Why We Did It**:
  - **Explainability**: For audit purposes, auditors must know *exactly* why a row was flagged as suspicious. "The neural network scored this 0.89 for anomaly" is not acceptable to an ESG auditor. A clear statement like "No Facility matches Meter ID 'MTR-9999'" is actionable and transparent.
  - **Data Scarcity**: ML models require a large history of clean data to learn normal seasonal consumption patterns. In onboarding a new enterprise client, no such baseline exists.
* **Production Alternative**: As facilities accumulate multi-year histories, we would introduce basic statistical thresholding (such as IQR or Z-score limits adjusted for seasonal weather variation) to flag consumption spikes.
`
