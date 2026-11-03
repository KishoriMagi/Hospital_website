# Hospital Patient and Lab Test Management Portal

A Flask web application for hospital staff to manage patient registrations, create diagnostic test requests, and view laboratory test results.

---

## About the Project

This project was built as a college project to simulate how a hospital portal interacts with an external diagnostic laboratory. 

Instead of combining the hospital and lab into one single database, this system uses an independent two-portal architecture:
1. **Hospital Portal (This repository):** Runs on port `5001`. Used by hospital staff and doctors to register patients, request medical tests, and view lab reports.
2. **Diagnostic Laboratory Portal (Separate project):** Runs on port `5000`. Used by lab technicians to receive samples, enter test values, and generate results.

Both portals maintain their own separate SQLite databases and communicate over **REST APIs** using a shared secret API key (`X-API-Key`).

---

## How It Works (Workflow)

1. **Staff Login:** Hospital staff logs in using their Staff ID and password.
2. **Patient Registration:** New patients are registered with their details (Name, Age, Gender, Doctor, Department, Phone, Emergency Contact).
3. **Test Request:** Staff selects a patient and creates a test request (Supported: CBC, Blood Sugar, Lipid Profile).
4. **API Transmission:** When the form is submitted, the Flask backend makes an HTTP `POST` request to the Laboratory Portal at `/api/requests` with JSON data and an `X-API-Key` header.
5. **Lab Processing:** The lab portal receives the request in "Pending" status. Lab technicians enter test readings (e.g., Hemoglobin, WBC, Platelets) and mark the test as Completed or Abnormal.
6. **Result Retrieval:** Hospital staff clicks **"Sync Results"** or **"Check Laboratory Result"**. The hospital backend calls `GET /api/results/<test_id>` to fetch the values, saves them in the local database, and displays the report on the portal.

---

## Project Structure

```
Hospital_website/
├── app.py                      # Main Flask application and blueprint registration
├── wsgi.py                     # Entry point for Gunicorn production server
├── config.py                   # Loads environment variables from .env
├── requirements.txt            # Python dependencies
├── render.yaml                 # Configuration file for Render deployment
├── database/
│   └── database.py             # SQLite connection and table creation
├── routes/
│   ├── auth.py                 # Staff login and logout routes
│   ├── patients.py             # Patient registration and dashboard routes
│   ├── test_requests.py        # Test request creation and API submission routes
│   └── results.py              # Test results viewing and sync routes
├── services/
│   ├── lab_api_service.py      # Makes REST API calls to the Laboratory Portal
│   └── result_sync_service.py  # Parses and saves incoming lab results
├── static/
│   ├── css/style.css           # Custom styling for dashboard and tables
│   └── js/app.js               # Auto-dismissing alerts and basic scripts
├── templates/                  # HTML templates with Bootstrap 5
│   ├── base.html               # Main layout and navigation sidebar
│   ├── dashboard.html          # Stats overview and recent activity
│   ├── login.html              # Staff login page
│   ├── patients.html           # List of registered patients
│   ├── patient_form.html       # Patient registration form
│   ├── patient_details.html    # Patient profile and medical history
│   ├── create_test_request.html# Form to order new lab tests
│   ├── test_requests.html      # Table of all test requests and their status
│   ├── test_request_details.html # Request details and result check button
│   ├── results.html            # Table of completed test results
│   └── result_details.html     # Report page showing test measurements
└── tests/
    ├── conftest.py             # Pytest setup and test database fixture
    └── test_app.py             # 7 unit tests covering auth, patients, and API
```

---

## Technology Stack

- **Backend:** Python 3.10+, Flask
- **Frontend:** HTML5, CSS3, Bootstrap 5, Bootstrap Icons, JavaScript
- **Database:** SQLite3 (`instance/hospital.db`)
- **HTTP Client:** Python `requests` library
- **WSGI Server:** Gunicorn (for Render deployment)
- **Testing:** Pytest

---

## Database Tables

The SQLite database (`hospital.db`) has 4 tables:
1. `users` - Stores staff accounts (`HOSP101`). Passwords are encrypted with Werkzeug hash.
2. `patients` - Stores patient demographic and contact information.
3. `test_requests` - Stores test requests, doctor name, priority, and current status (`Pending`, `Sent to Laboratory`, `Completed`, `Abnormal`).
4. `test_results` - Stores incoming test readings in JSON format, laboratory remarks, and processed dates.

*Note on Render deployment: Because this project uses local SQLite, data on Render's free plan resets whenever the free container spins down after 15 minutes of inactivity. For permanent storage in production, a PostgreSQL database or Render Persistent Disk should be used.*

---

## Setting Up and Running Locally

### 1. Navigate to the project folder
```bash
cd Hospital_website
```

### 2. Create and activate a virtual environment
- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **On Mac / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install required packages
```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file
Copy `.env.example` to `.env`:
- **Windows:** `copy .env.example .env`
- **Mac/Linux:** `cp .env.example .env`

Configure the values:
```ini
PORT=5001
SECRET_KEY=my_hospital_secret_key_2026

# Laboratory REST API settings
LAB_API_URL=http://127.0.0.1:5000
LAB_API_KEY=your-laboratory-api-key
LAB_API_TIMEOUT=15
USE_REST_API=True
```

### 5. Start the Flask application
```bash
python app.py
```

Open your browser and visit: **`http://127.0.0.1:5001`**

---

## Default Login Credentials

- **Staff ID:** `HOSP101`
- **Password:** `admin123`

*(This account is created automatically the first time the app runs).*

---

## Running the Tests

To run the automated tests:
```bash
pytest
```
All 7 unit tests will run and verify login, patient creation, duplicate checks, API request dispatch, and result syncing.

---

## Deploying on Render

1. Push this project to GitHub.
2. Go to **Render Dashboard** → **New +** → **Web Service**.
3. Select your repository.
4. Settings:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Add the Environment Variables:
   - `SECRET_KEY`: any random secret text
   - `LAB_API_URL`: URL of your deployed laboratory portal (e.g., `https://your-lab.onrender.com`)
   - `LAB_API_KEY`: the agreed secret API key
   - `LAB_API_TIMEOUT`: `15`
   - `USE_REST_API`: `True`
