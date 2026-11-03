import os
import json
from unittest.mock import patch
from services.lab_api_service import LabApiService


def test_login(client, auth):
    response = auth.login()
    assert response.headers['Location'] == '/dashboard'
    
    response = client.get('/dashboard')
    assert b'Dashboard' in response.data


def test_patient_registration(client, auth, app):
    auth.login()
    response = client.post('/patients/create', data={
        'patient_id': 'P1023',
        'patient_name': 'Rahul',
        'age': 23,
        'gender': 'Male',
        'date_of_birth': '2003-05-10',
        'phone': '1234567890',
        'email': 'rahul@example.com',
        'address': 'Test Address',
        'emergency_contact': 'Mom 0987654321',
        'doctor': 'Dr. Kumar',
        'department': 'General'
    })
    
    assert response.headers['Location'] == '/patients'
    
    with app.app_context():
        from database.database import get_db
        db = get_db()
        patient = db.execute('SELECT * FROM patients WHERE patient_id = "P1023"').fetchone()
        assert patient is not None
        assert patient['patient_name'] == 'Rahul'


def test_duplicate_patient_id(client, auth, app):
    auth.login()
    client.post('/patients/create', data={
        'patient_id': 'P1024',
        'patient_name': 'Alice',
        'age': 30,
        'gender': 'Female',
        'date_of_birth': '', 'phone': '', 'email': '', 'address': '', 'emergency_contact': '', 'doctor': '', 'department': ''
    })
    response = client.post('/patients/create', data={
        'patient_id': 'P1024',
        'patient_name': 'Bob',
        'age': 25,
        'gender': 'Male',
        'date_of_birth': '', 'phone': '', 'email': '', 'address': '', 'emergency_contact': '', 'doctor': '', 'department': ''
    })
    assert b'already registered' in response.data


def test_test_request_creation_rest_api_success(client, auth, app, monkeypatch):
    auth.login()
    
    # Register patient
    client.post('/patients/create', data={
        'patient_id': 'P1023', 'patient_name': 'Rahul', 'age': 23, 'gender': 'Male',
        'date_of_birth': '', 'phone': '', 'email': '', 'address': '', 'emergency_contact': '', 'doctor': 'Dr. Kumar', 'department': ''
    })

    # Mock LabApiService.create_test_request to return successful response
    def mock_create(self, payload):
        assert payload['test_id'] == 'T1001'
        assert payload['patient_id'] == 'P1023'
        assert payload['test_type'] == 'CBC'
        return True, {'success': True, 'message': 'Received'}, '', 201

    monkeypatch.setattr(LabApiService, 'create_test_request', mock_create)
    
    response = client.post('/test-requests/create', data={
        'patient_id': 'P1023',
        'test_id': 'T1001',
        'test_type': 'CBC',
        'sample_type': 'Blood',
        'priority': 'Normal',
        'requested_date': '2026-10-07',
        'instructions': 'Regular CBC test'
    })
    
    assert response.headers['Location'] == '/test-requests/'
    
    with app.app_context():
        from database.database import get_db
        db = get_db()
        req = db.execute('SELECT * FROM test_requests WHERE test_id = "T1001"').fetchone()
        assert req is not None
        assert req['status'] == 'Sent to Laboratory'
        assert req['dropbox_file_path'] == 'REST_API'


def test_test_request_rejection_by_lab(client, auth, app, monkeypatch):
    auth.login()
    
    # Register patient
    client.post('/patients/create', data={
        'patient_id': 'P1025', 'patient_name': 'Meera', 'age': 29, 'gender': 'Female',
        'date_of_birth': '', 'phone': '', 'email': '', 'address': '', 'emergency_contact': '', 'doctor': 'Dr. Kumar', 'department': ''
    })

    # Mock LabApiService.create_test_request to simulate Lab API rejection (e.g. duplicate or validation failure)
    def mock_create_fail(self, payload):
        return False, {'success': False}, "Test request with ID 'T1002' already exists.", 409

    monkeypatch.setattr(LabApiService, 'create_test_request', mock_create_fail)
    
    response = client.post('/test-requests/create', data={
        'patient_id': 'P1025',
        'test_id': 'T1002',
        'test_type': 'CBC',
        'sample_type': 'Blood',
        'priority': 'Normal',
        'requested_date': '2026-10-07',
        'instructions': 'Test failure'
    })
    
    assert response.status_code == 200
    assert b"Submission rejected by Laboratory Portal" in response.data
    
    with app.app_context():
        from database.database import get_db
        db = get_db()
        req = db.execute('SELECT * FROM test_requests WHERE test_id = "T1002"').fetchone()
        # Request must NOT be marked as sent or saved
        assert req is None


def test_fetch_single_result(client, auth, app, monkeypatch):
    auth.login()
    
    # Insert test request directly into DB
    with app.app_context():
        from database.database import get_db
        db = get_db()
        db.execute(
            "INSERT INTO patients (patient_id, patient_name, age, gender) VALUES ('P1026', 'Vikram', 35, 'Male')"
        )
        db.execute(
            """INSERT INTO test_requests (test_id, patient_id, patient_name, age, gender, doctor,
               test_type, sample_type, priority, requested_date, status, dropbox_file_path)
               VALUES ('T1003', 'P1026', 'Vikram', 35, 'Male', 'Dr. Kumar', 'CBC', 'Blood', 'Normal', '2026-10-07', 'Sent to Laboratory', 'REST_API')"""
        )
        db.commit()

    # Mock get_test_result returning completed data
    def mock_get_result(self, test_id):
        assert test_id == 'T1003'
        return True, {
            'test_id': 'T1003',
            'patient_id': 'P1026',
            'test_type': 'CBC',
            'result_status': 'Normal',
            'measurements': {'Hemoglobin': 14.2, 'WBC': 6800},
            'remarks': 'All normal',
            'processed_date': '2026-10-26'
        }, '', False

    monkeypatch.setattr(LabApiService, 'get_test_result', mock_get_result)

    response = client.post('/test-requests/T1003/fetch-result')
    assert response.headers['Location'] == '/results/T1003'

    with app.app_context():
        from database.database import get_db
        db = get_db()
        result = db.execute("SELECT * FROM test_results WHERE test_id = 'T1003'").fetchone()
        assert result is not None
        assert result['result_status'] == 'Normal'
        req = db.execute("SELECT * FROM test_requests WHERE test_id = 'T1003'").fetchone()
        assert req['status'] == 'Completed'


def test_sync_results_via_rest_api(client, auth, app, monkeypatch):
    auth.login()

    with app.app_context():
        from database.database import get_db
        db = get_db()
        db.execute("INSERT INTO patients (patient_id, patient_name) VALUES ('P1027', 'Suresh')")
        db.execute(
            """INSERT INTO test_requests (test_id, patient_id, patient_name, age, gender, doctor,
               test_type, sample_type, priority, requested_date, status)
               VALUES ('T1004', 'P1027', 'Suresh', 40, 'Male', 'Dr. Kumar', 'Blood Sugar', 'Blood', 'Urgent', '2026-10-07', 'Sent to Laboratory')"""
        )
        db.commit()

    def mock_get_all(self):
        return True, [{
            'test_id': 'T1004',
            'patient_id': 'P1027',
            'test_type': 'Blood Sugar',
            'result_status': 'Abnormal',
            'measurements': {'Glucose': 185.0},
            'remarks': 'Elevated glucose',
            'processed_date': '2026-10-26'
        }], ''

    monkeypatch.setattr(LabApiService, 'get_all_completed_results', mock_get_all)
    monkeypatch.setattr(LabApiService, 'get_test_result', lambda self, tid: (False, {}, 'Not found', False))

    response = client.post('/results/sync')
    assert response.headers['Location'] == '/results/'

    with app.app_context():
        from database.database import get_db
        db = get_db()
        result = db.execute("SELECT * FROM test_results WHERE test_id = 'T1004'").fetchone()
        assert result is not None
        assert result['result_status'] == 'Abnormal'
        req = db.execute("SELECT * FROM test_requests WHERE test_id = 'T1004'").fetchone()
        assert req['status'] == 'Abnormal'
