import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.database import get_db
import csv

def generate_samples():
    app = create_app()
    with app.app_context():
        db = get_db()
        
        # Insert patients
        patients = [
            ('P1001', 'John Doe', 45, 'Male', '1981-05-12', '123-456-7890', 'john@example.com', '123 Main St', 'Jane Doe', 'Dr. Smith', 'Cardiology'),
            ('P1002', 'Jane Smith', 32, 'Female', '1994-08-23', '098-765-4321', 'jane@example.com', '456 Oak Ave', 'John Smith', 'Dr. Adams', 'General'),
            ('P1003', 'Bob Johnson', 58, 'Male', '1968-11-05', '555-123-4567', 'bob@example.com', '789 Pine Rd', 'Mary Johnson', 'Dr. Lee', 'Endocrinology')
        ]
        
        for p in patients:
            if not db.execute('SELECT id FROM patients WHERE patient_id = ?', (p[0],)).fetchone():
                db.execute(
                    '''INSERT INTO patients (patient_id, patient_name, age, gender, date_of_birth, phone, email, address, emergency_contact, doctor, department)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', p
                )
                
        # Insert test requests
        requests = [
            ('T1001', 'P1001', 'John Doe', 45, 'Male', 'Dr. Smith', 'CBC', 'Blood', 'Normal', '2026-10-07', 'Routine checkup'),
            ('T1002', 'P1002', 'Jane Smith', 32, 'Female', 'Dr. Adams', 'Blood Sugar', 'Blood', 'Urgent', '2026-10-07', 'Fasting'),
            ('T1003', 'P1003', 'Bob Johnson', 58, 'Male', 'Dr. Lee', 'Lipid Profile', 'Blood', 'Normal', '2026-10-06', 'Cholesterol check')
        ]
        
        for r in requests:
            if not db.execute('SELECT id FROM test_requests WHERE test_id = ?', (r[0],)).fetchone():
                db.execute(
                    '''INSERT INTO test_requests (test_id, patient_id, patient_name, age, gender, doctor, test_type, sample_type, priority, requested_date, instructions)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', r
                )
        
        db.commit()
        print("Sample data populated in database.")
        
        # Generate sample request CSV files
        requests_dir = os.path.join(app.config['MOCK_REQUESTS_DIR'])
        os.makedirs(requests_dir, exist_ok=True)
        
        # Generate T1001
        with open(os.path.join(requests_dir, 'test_request_T1001.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Patient_ID', 'Patient_Name', 'Age', 'Gender', 'Doctor', 'Test_ID', 'Test_Type', 'Sample_Type', 'Priority', 'Requested_Date', 'Instructions'])
            w.writerow(['P1001', 'John Doe', 45, 'Male', 'Dr. Smith', 'T1001', 'CBC', 'Blood', 'Normal', '2026-10-07', 'Routine checkup'])
            
        print("Sample requests CSV files generated.")
        
        # Generate sample result CSV files for the mock
        results_dir = os.path.join(app.config['MOCK_RESULTS_DIR'])
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate T1001 CBC result
        with open(os.path.join(results_dir, 'test_result_T1001.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Patient_ID', 'Test_ID', 'Test_Type', 'Hemoglobin', 'WBC', 'RBC', 'Platelets', 'Result_Status', 'Processed_Date', 'Remarks'])
            w.writerow(['P1001', 'T1001', 'CBC', '13.8', '7200', '4.9', '250000', 'Normal', '2026-10-07', 'Within reference range'])
            
        # Generate T1002 Blood Sugar result
        with open(os.path.join(results_dir, 'test_result_T1002.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Patient_ID', 'Test_ID', 'Test_Type', 'Glucose', 'Unit', 'Result_Status', 'Processed_Date', 'Remarks'])
            w.writerow(['P1002', 'T1002', 'Blood Sugar', '150', 'mg/dL', 'Abnormal', '2026-10-07', 'High glucose level'])
            
        # Generate an invalid one
        with open(os.path.join(results_dir, 'test_result_T9999.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Patient_ID', 'Test_ID', 'Test_Type', 'Result_Status', 'Processed_Date'])
            w.writerow(['P9999', 'T9999', 'CBC', 'Normal', '2026-10-07'])
            
        print("Sample results CSV files generated.")

if __name__ == '__main__':
    generate_samples()
