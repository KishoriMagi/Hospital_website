# Project Writeup: Diagnostic Laboratory Processing Portal

---

## 1. Title
**Development of an Automated Pathological Diagnostic Processing Engine and REST API for Clinical Laboratories**

---

## 2. Motivation
Clinical diagnostic laboratories are high-throughput environments responsible for analyzing biological specimens and turning raw physical analyzer data into diagnostic findings. In standard pathological workflows, laboratory technicians frequently handle manual sample logs, perform repetitive manual comparisons against medical reference books, and manually type paper reports. This traditional workflow is prone to transcription error, high turnaround latency, and loss of critical diagnostic details.

The motivation behind developing the Diagnostic Laboratory Processing Portal is to deliver an automated, secure laboratory information management system (LIMS). By providing a digital technician workstation, automated reference interval evaluation, and programmatic RESTful endpoints to receive hospital test orders, this portal minimizes human error, standardizes diagnostic reporting, and ensures rapid delivery of critical pathology results.

---

## 3. Existing Gap / Event that Motivated the Project / USP

### Existing Gaps & Trigger Events
1. **Third-Party File-Drop Storage Bottlenecks**: Previously, orders were received via Dropbox CSV file polling. This approach suffered from file-lock collisions, token expirations every 4 hours, and unexpected network DNS drops (`Errno 11001: getaddrinfo failed`).
2. **Subjective Manual Range Evaluation**: Manual interpretation of clinical numbers (e.g., distinguishing whether a Hemoglobin level of 11.2 g/dL is normal for adult males versus adult females) introduces human variability and risks overlooking borderline pathology.
3. **Absence of Real-Time Validation**: Legacy batch uploads allowed malformed or duplicate test IDs to enter the laboratory pipeline before errors were detected, resulting in lost work hours.

### Unique Selling Proposition (USP)
* **Automated Diagnostic Evaluation Engine (`services/processing_service.py`)**: Instant mathematical comparison of raw laboratory measurements against established clinical reference intervals to assign classification flags (`Normal`, `Abnormal`, `Critical`).
* **Protected Dual-Mode Operation**: Seamlessly provides a web-based GUI for human technicians while simultaneously serving a secured, token-authenticated REST API for external hospital automation.
* **Strict Schema & Duplicate Enforcement**: Built-in validation service (`services/validation_service.py`) rejects duplicate test IDs and corrupted payloads at the network boundary with explicit HTTP status codes (`409 Conflict`, `400 Bad Request`).
* **Audit-Ready Persistence & CSV Generation**: Dual retention—stores all transactions atomically in SQLite (`laboratory.db`) while also generating standardized, exportable CSV reports for medical accreditation audits.

---

## 4. Architecture
The Laboratory Portal operates as an independent backend service and technician workstation running on **Port 5000**.

> **Architecture Diagram File**: See [`laboratory_architecture_diagram.svg`](file:///D:/Hospital_website/laboratory_architecture_diagram.svg) for the full 5-tier elaborated diagram.

```
+---------------------------------------------------------------------------------+
|                    DIAGNOSTIC LABORATORY PORTAL (Port 5000)                     |
|                                                                                 |
|  [External Hospital (Port 5001)]                    [Laboratory Technicians]    |
|            |                                                   |                |
|            | (HTTP REST Calls)                                 | (Browser UI)   |
|            v                                                   v                |
|   [@require_api_key Gate]                            [Session Auth / UI]        |
|            |                                                   |                |
|            +-------------------> [Flask Router] <---------------+                |
|                                         |                                       |
|              +--------------------------+--------------------------+            |
|              |                          |                          |            |
|              v                          v                          v            |
|   [validation_service.py]    [processing_service.py]     [laboratory.db]        |
|   (Schema / Deduplication)   (Reference Intervals)       (Atomic Storage)       |
+---------------------------------------------------------------------------------+
```

### Architectural Tiers
* **Security & Ingress Layer**: Dual-mode authentication—Flask session authentication for human technicians and `@require_api_key` decorator enforcing `X-API-Key` headers for automated REST consumers.
* **Controller Tier**: Flask routes organizing technician views (`tests`, `dashboard`, `auth`) and programmatic endpoints (`routes/api.py`).
* **Business Logic & Evaluation Tier**:
  * `services/validation_service.py`: Inspects payload structure, verifies test types, and prevents duplicate requisitions.
  * `services/processing_service.py`: Encapsulates clinical reference interval logic for multi-parameter panels (CBC, Lipid, Metabolic).
  * `Pandas CSV Engine`: Compiles structured laboratory records into compliance-ready CSV exports.
* **Persistence Tier**: SQLite3 database (`laboratory.db`) maintaining records of incoming orders, biological specimen statuses, and verified diagnostic metrics.

---

## 5. Complete Tech Stack Information
* **Core Language**: Python 3.10+
* **Backend Framework**: Flask
* **Data Processing & Scientific Libraries**: Pandas, NumPy (for tabular data extraction and numerical range calculations)
* **Web Server & Gateway**: Werkzeug WSGI (Development), Gunicorn WSGI (Production)
* **Frontend Technologies**: HTML5, CSS3, JavaScript, Bootstrap 5, Jinja2
* **Relational Database**: SQLite3 (Isolated relational database with transaction locking)
* **Security Layer**: Custom Decorator Authentication (`@require_api_key`), PBKDF2 Password Hashing
* **Deployment & Containerization**: Render PaaS configuration (`render.yaml`, `wsgi.py`)

---

## 6. Datasets Used

### Relational Database Schema (`laboratory.db`)
1. **`users` Table**:
   * Attributes: `id` (INT PK), `username` (VARCHAR), `password_hash` (VARCHAR), `role` (VARCHAR: Technician, Pathologist, Admin), `created_at` (DATETIME).
2. **`test_requests` Table**:
   * Attributes: `id` (INT PK), `test_id` (VARCHAR UNIQUE), `patient_name` (VARCHAR), `test_type` (VARCHAR), `priority` (VARCHAR), `status` (VARCHAR: Pending, In Processing, Completed), `received_via` (VARCHAR: REST_API), `created_at` (DATETIME).
3. **`test_results` Table**:
   * Attributes: `id` (INT PK), `test_id` (FK), `parameter_name` (VARCHAR), `measured_value` (FLOAT/VARCHAR), `unit` (VARCHAR), `reference_range` (VARCHAR), `interpretation` (VARCHAR: Normal/Abnormal), `technician_remarks` (TEXT), `completed_at` (DATETIME).

### Pathological Reference Interval Catalog
Built-in standard pathological reference dataset encompassing standard diagnostic panels:
* **Complete Blood Count (CBC)**:
  * *Hemoglobin*: $13.8 - 17.2\text{ g/dL}$ (Male), $12.1 - 15.1\text{ g/dL}$ (Female)
  * *White Blood Cell Count (WBC)*: $4,500 - 11,000\text{ cells/}\mu\text{L}$
  * *Platelet Count*: $150,000 - 450,000/\mu\text{L}$
* **Lipid Profile**:
  * *Total Cholesterol*: $< 200\text{ mg/dL}$ (Desirable)
  * *Triglycerides*: $< 150\text{ mg/dL}$
  * *HDL Cholesterol*: $> 40\text{ mg/dL}$
  * *LDL Cholesterol*: $< 100\text{ mg/dL}$
* **Blood Glucose**:
  * *Fasting Blood Sugar (FBS)*: $70 - 99\text{ mg/dL}$

---

## 7. List of Prompts Used for the Construction of the Website
1. *"Create a modular Flask web application for a diagnostic laboratory that exposes RESTful endpoints to receive test orders and publish verified results."*
2. *"Implement a Python decorator `@require_api_key` that inspects incoming HTTP requests for an `X-API-Key` header and returns a JSON 401 error response if the key is missing or invalid."*
3. *"Write a validation service in Python that validates incoming test requisition JSON payloads, ensures all required medical parameters exist, and prevents duplicate test ID creation."*
4. *"Build an automated clinical reference interval engine in Python that evaluates numeric laboratory measurements against standard medical bounds and assigns qualitative flags (Normal, High, Low, Abnormal)."*
5. *"Develop a technician workstation UI using Bootstrap 5 where staff can select pending test orders, enter raw analyzer readings, review automated calculations, and finalize reports."*

---

## 8. API Integration

### Role: REST API Server / Provider
The Laboratory Portal provides secure HTTP endpoints accessed by the Hospital Portal.

#### 1. Inbound Test Request Receiver
* **HTTP Method & Route**: `POST /api/requests`
* **Access Control**: Protected by `@require_api_key`
* **Request Header Required**: `X-API-Key: <SHARED_LABORATORY_SECRET_KEY>`
* **Validation & Processing**:
  * Parses incoming JSON payload.
  * Queries `laboratory.db` for existing `test_id`.
  * If found, returns HTTP `409 Conflict`:
    ```json
    { "success": false, "error": "Test ID already exists in laboratory database." }
    ```
  * If valid, inserts into `test_requests` (status: `Pending`) and returns HTTP `201 Created`:
    ```json
    {
      "success": true,
      "message": "Test request queued successfully",
      "test_id": "REQ-2026-101"
    }
    ```

#### 2. Outbound Test Result Provider
* **HTTP Method & Route**: `GET /api/results/<test_id>`
* **Access Control**: Protected by `@require_api_key`
* **Response Handling**:
  * If test status is `Pending` or `In Processing`, returns HTTP `404 Not Found`:
    ```json
    { "success": false, "status": "Pending", "message": "Results not yet finalized." }
    ```
  * If test is completed, returns HTTP `200 OK`:
    ```json
    {
      "success": true,
      "test_id": "REQ-2026-101",
      "status": "Completed",
      "test_type": "Complete Blood Count",
      "measurements": {
        "Hemoglobin": "11.2 g/dL",
        "WBC": "12,400 /mcL",
        "Platelets": "220,000 /mcL"
      },
      "interpretation": "Abnormal",
      "technician_notes": "Mild anemia and elevated WBC count noted.",
      "completed_at": "2026-11-01T14:30:00Z"
    }
    ```

---

## 9. Users, Inputs (Types, Formats), and Outputs

### System Users
1. **Laboratory Technicians**: Review incoming test queues, record instrument measurements, verify automated reference assessments.
2. **Pathologists / Laboratory Directors**: Review flagged abnormal samples, author clinical interpretations, sign off on finalized findings.
3. **Hospital REST API Client (Automated System)**: Server process transmitting requisitions and pulling finalized reports.

### Input Types & Formats
* **Inbound JSON Requisition Payloads**: Structured strings (`test_id`, `patient_name`, `test_type`, `priority`), ISO date formats.
* **Technician Measurement Forms**: Floating-point numeric inputs (e.g., Hemoglobin `14.2`, Glucose `110.5`), integer counts (e.g., Platelets `250000`, WBC `7800`), free-text notes.
* **Status Updates**: Dropdown transitions (`Pending` $\rightarrow$ `In Processing` $\rightarrow$ `Completed`).

### System Outputs
* **Automated Diagnostic Classifications**: Parameter-level evaluation badges (`Normal`, `Low`, `High`, `Critical`).
* **Standardized JSON Responses**: High-speed, structured output delivered over HTTP to partner hospital systems.
* **Historical CSV Exports**: Pandas-compiled CSV files storing all completed diagnostic records for offline archival and audit trails.

---

## 10. References
1. World Health Organization (WHO). *Good Clinical Laboratory Practice (GCLP) Guidelines*.
2. Tietz, N. W. (2006). *Tietz Clinical Guide to Laboratory Tests*. Elsevier Health Sciences.
3. Pallets Projects. *Flask Documentation (v3.0.x) - Application Factories and Blueprints*.
4. Richardson, L., & Ruby, S. (2007). *RESTful Web Services*. O'Reilly Media.
5. Clinical and Laboratory Standards Institute (CLSI). *Defining, Establishing, and Verifying Reference Intervals in the Clinical Laboratory*.
