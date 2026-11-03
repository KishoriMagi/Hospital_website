# Project Writeup: Hospital Patient & Test Management Portal

---

## 1. Title
**Design and Implementation of a Secure, REST-Integrated Hospital Patient and Laboratory Diagnostic Management System**

---

## 2. Motivation
In modern healthcare environments, rapid and accurate communication between clinical wards and pathology laboratories is vital for timely medical intervention. Traditionally, hospitals have grappled with paper-based test requisitions, physical sample transit slips, and delayed manual report collection. These legacy practices introduce administrative bottlenecks, increase transcriptional errors, and delay critical patient diagnoses. 

The primary motivation of this project is to create an intuitive, digitized, and highly available clinical interface for hospital physicians and administrative staff. By providing direct patient management, streamlined diagnostic test ordering, and real-time electronic result synchronization, this portal empowers medical professionals to make faster, evidence-based diagnostic decisions while safeguarding sensitive patient health records.

---

## 3. Existing Gap / Event that Motivated the Project / USP

### Existing Gaps & Trigger Events
1. **Third-Party API Fragility & Token Lifespan**: Previous iterations relied on external third-party cloud storage (such as the Dropbox API) to transfer batch CSV order files. In real-time production, standard developer tokens expire every 4 hours, requiring complex OAuth refresh mechanics or costly enterprise subscriptions.
2. **Network Failures & Unresolved DNS**: Third-party cloud dependencies introduce external failure vectors (e.g., `Errno 11001: getaddrinfo failed` when firewalls or campus networks fail to resolve external endpoints).
3. **Asynchronous Polling Delay**: File-drop systems lack immediate confirmation. Clinicians could not verify whether an emergency diagnostic order was acknowledged by the laboratory without waiting for asynchronous polling loops.

### Unique Selling Proposition (USP)
* **Direct Server-to-Server REST Architecture**: Complete removal of intermediate cloud relays. Test requisitions and diagnostic outcomes travel directly between the hospital and laboratory backend services via high-speed HTTP requests.
* **Strict Data Sovereignty & Isolation**: The hospital relational database (`hospital.db`) remains completely independent. No direct database queries or credentials are cross-shared between facilities.
* **Synchronous Transactional Validation**: Immediate HTTP response codes (e.g., HTTP `201 Created` vs. HTTP `409 Conflict` or `400 Bad Request`) give doctors instant, real-time feedback on test order validity.
* **Header-Based Token Security**: Requests are cryptographically authorized via server-level `X-API-Key` headers, isolating internal networks from unauthorized access.

---

## 4. Architecture
The Hospital Portal is architected as an independent, modular service deployed on **Port 5001**.

> **Architecture Diagram File**: See [`hospital_architecture_diagram.svg`](file:///D:/Hospital_website/hospital_architecture_diagram.svg) for the full 5-tier elaborated diagram.

```
+---------------------------------------------------------------------------------+
|                         HOSPITAL PORTAL (Port 5001)                             |
|                                                                                 |
|   [Clinician / Staff] <---> [Browser / Bootstrap 5 UI]                          |
|                                      |                                          |
|                               (HTTP Form / AJAX)                                |
|                                      v                                          |
|                       [Flask Application Factory]                               |
|                         (Modular Blueprints)                                    |
|                                      |                                          |
|                +---------------------+---------------------+                    |
|                |                                           |                    |
|                v                                           v                    |
|   [Persistence Layer]                             [REST Service Layer]          |
|   - SQLite3 (hospital.db)                         - services/lab_api_service.py |
|   - Patients & Test Orders                        - services/result_sync_service|
+------------------------------------------------------------|--------------------+
                                                             |
                           1. POST /api/requests (JSON Order)| (Header: X-API-Key)
                           2. GET /api/results/<id> (Result) |
                                                             v
                                            [Laboratory Portal (Port 5000)]
```

### Architectural Tiers
* **Presentation Tier**: HTML5, Jinja2 templating, Bootstrap 5 UI framework, and FontAwesome icons delivering a mobile-responsive clinical workstation.
* **Application / Controller Tier**: Python Flask application organized using modular blueprints (`patients`, `test_requests`, `results`, `auth`).
* **Service / Integration Layer**:
  * `services/lab_api_service.py`: Serializes clinical orders into compliant JSON structures and manages outbound HTTP `POST` requests.
  * `services/result_sync_service.py`: Periodically queries the diagnostic laboratory via HTTP `GET` to pull completed findings into the hospital records.
* **Persistence Tier**: SQLite3 database (`hospital.db`) maintaining normalized tables for users, patient demographics, and test requisitions.

---

## 5. Complete Tech Stack Information
* **Core Language**: Python 3.10+
* **Backend Framework**: Flask (Microframework with Blueprints architecture)
* **WSGI & Web Gateway**: Werkzeug (Development Server), Gunicorn WSGI (Production Server)
* **Frontend Technologies**: HTML5, CSS3, JavaScript (ES6), Bootstrap 5, Jinja2 Templating
* **Relational Database**: SQLite3 (Transactional, ACID-compliant file-based RDBMS)
* **HTTP & API Client**: Python `requests` library
* **Configuration & Environment**: `python-dotenv` for environment variable injection (`.env`)
* **Security & Cryptography**: Werkzeug Security (`generate_password_hash`, `check_password_hash`)
* **Deployment & Containerization**: Render PaaS configuration (`render.yaml`, `wsgi.py`)

---

## 6. Datasets Used

### Relational Database Schema (`hospital.db`)
1. **`users` Table**:
   * Attributes: `id` (INT PK), `username` (VARCHAR), `password_hash` (VARCHAR), `role` (VARCHAR: Doctor, Nurse, Admin), `created_at` (DATETIME).
2. **`patients` Table**:
   * Attributes: `id` (INT PK), `patient_id` (VARCHAR UNIQUE), `name` (VARCHAR), `age` (INT), `gender` (VARCHAR), `contact_number` (VARCHAR), `blood_group` (VARCHAR), `medical_history` (TEXT), `registered_at` (DATETIME).
3. **`test_requests` Table**:
   * Attributes: `id` (INT PK), `test_id` (VARCHAR UNIQUE), `patient_id` (FK), `test_type` (VARCHAR), `priority` (VARCHAR: Routine/Urgent/Stat), `prescribing_doctor` (VARCHAR), `status` (VARCHAR: Draft/Sent to Laboratory/In Processing/Completed), `transmission_mode` (VARCHAR: REST_API), `created_at` (DATETIME).
4. **`test_results` Table**:
   * Attributes: `id` (INT PK), `test_id` (FK), `patient_id` (FK), `parameters_json` (TEXT), `interpretation` (VARCHAR: Normal/Abnormal), `technician_remarks` (TEXT), `synced_at` (DATETIME).

### Synthetic & Test Cohort Data
* Curated synthetic patient datasets representing typical outpatient cohorts (demographics, contact info, standard clinical histories) and realistic test orders (Complete Blood Count, Lipid Profile, Liver Function Test, Renal Function Test).

---

## 7. List of Prompts Used for the Construction of the Website
1. *"Design and structure a production-ready Flask hospital management web application featuring patient registration, test ordering, and SQLite database storage."*
2. *"Refactor the hospital test order dispatch engine to completely remove the Dropbox API and implement a direct REST client using Python `requests` with custom HTTP headers (`X-API-Key`)."*
3. *"Build a result synchronization service in Python that connects to an external laboratory API endpoint `GET /api/results/<test_id>`, securely ingesting test findings and marking orders as completed in the local database."*
4. *"Create responsive Bootstrap 5 templates with dynamic badges that visually highlight abnormal test values and alert clinicians of urgent diagnostic results."*
5. *"Write configuration files (`render.yaml`, `wsgi.py`) to deploy the Hospital Flask portal seamlessly to Render using Gunicorn."*

---

## 8. API Integration

### Role: REST Client
The Hospital Portal operates as a client that establishes authenticated HTTP connections to the Laboratory Portal (`http://localhost:5000` or production URL).

#### 1. Outbound Test Request Dispatch
* **HTTP Method & Route**: `POST /api/requests`
* **Request Headers**:
  ```http
  Content-Type: application/json
  X-API-Key: <SECURE_HOSPITAL_LAB_API_KEY>
  ```
* **Request Body (JSON)**:
  ```json
  {
    "test_id": "REQ-2026-101",
    "patient_id": "PAT-4021",
    "patient_name": "Eleanor Vance",
    "test_type": "Complete Blood Count",
    "priority": "Urgent",
    "sample_type": "Whole Blood",
    "prescribing_doctor": "Dr. Sarah Jenkins",
    "order_date": "2026-11-01"
  }
  ```
* **Response Handling**:
  * `201 Created`: Updates local record to `Sent to Laboratory`.
  * `400 Bad Request`: Displays validation error on UI; aborts local transaction.
  * `409 Conflict`: Alerts doctor that the Test ID already exists in the laboratory system.
  * `401 Unauthorized`: Triggers authentication error alerting administrator to verify API keys.

#### 2. Inbound Result Synchronization Query
* **HTTP Method & Route**: `GET /api/results/<test_id>`
* **Request Headers**: `X-API-Key: <SECURE_HOSPITAL_LAB_API_KEY>`
* **Response Handling**:
  * `200 OK`: Ingests result values into `test_results`, marks status as `Completed`, and notifies the doctor.
  * `404 Not Found`: Flags test as `In Processing` at the laboratory.

---

## 9. Users, Inputs (Types, Formats), and Outputs

### System Users
1. **Attending Doctors / Clinicians**: Prescribe diagnostic tests, review patient medical histories, evaluate pathology findings.
2. **Hospital Nursing / Ward Staff**: Register incoming patients, update contact profiles, track pending laboratory test statuses.
3. **Hospital Administrators**: Manage user access, configure portal security parameters, audit system logs.

### Input Types & Formats
* **Patient Registration Data**:
  * Text Fields: Full Name, Address, Contact Number (Regex-validated phone strings).
  * Numeric: Age (Integer, 0–120).
  * Categorical Dropdowns: Gender (`Male`, `Female`, `Other`), Blood Group (`A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-`).
* **Test Requisition Data**:
  * Alphanumeric ID: `test_id` (e.g., `REQ-2026-101`).
  * Dropdown Selection: `test_type` (CBC, Lipid Profile, Renal Function, Blood Glucose).
  * Priority Level: `Routine`, `Urgent`, `Stat`.
* **Search / Filter Query Inputs**: Alphanumeric patient IDs or date range selectors.

### System Outputs
* **Clinical Management Dashboard**: Real-time counter cards showing active patients, pending test requests, and newly received diagnostic results.
* **Formatted Diagnostic Reports**: Clean, color-coded tables summarizing test parameters, observed patient values, standard medical reference intervals, and status flags (`Normal` vs. `Abnormal`).
* **Print-Ready Medical Certificates**: Browser-printable, clean clinical summaries formatted for physical patient records.

---

## 10. References
1. Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures* (Doctoral dissertation, University of California, Irvine).
2. Grinberg, M. (2018). *Flask Web Development: Developing Web Applications with Python*. O'Reilly Media.
3. Health Level Seven International (HL7). *Fast Healthcare Interoperability Resources (FHIR) Specification - DiagnosticReport & ServiceRequest*.
4. Rescorla, E. (2018). *The Transport Layer Security (TLS) Protocol Version 1.3*. RFC 8446.
5. World Health Organization (WHO). *Digital Health Guidelines on Data Exchange and Patient Identification*.
