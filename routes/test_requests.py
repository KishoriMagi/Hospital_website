import os
import csv
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, current_app
from werkzeug.exceptions import abort
from routes.auth import login_required
from database.database import get_db
from services.lab_api_service import LabApiService
from services.dropbox_service import DropboxService
from services.result_sync_service import ResultSyncService

bp = Blueprint('test_requests', __name__, url_prefix='/test-requests')


@bp.route('/')
@login_required
def index():
    db = get_db()
    requests = db.execute('SELECT * FROM test_requests ORDER BY created_at DESC').fetchall()
    return render_template('test_requests.html', requests=requests)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    db = get_db()

    if request.method == 'POST':
        patient_id = request.form.get('patient_id', '').strip()
        test_id = request.form.get('test_id', '').strip()
        test_type = request.form.get('test_type', '').strip()
        sample_type = request.form.get('sample_type', '').strip()
        priority = request.form.get('priority', '').strip()
        requested_date = request.form.get('requested_date', '').strip()
        instructions = request.form.get('instructions', '').strip()

        error = None

        # Validation
        patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
        if not patient:
            error = f"Patient ID {patient_id} not found."
        elif db.execute('SELECT id FROM test_requests WHERE test_id = ?', (test_id,)).fetchone() is not None:
            error = f"Test ID {test_id} is already in use in Hospital records."

        if not test_type or not sample_type or not priority or not requested_date:
            error = "All required fields must be filled."

        if error is not None:
            flash(error, 'danger')
        else:
            use_rest_api = current_app.config.get('USE_REST_API', True)

            if use_rest_api:
                # Prepare JSON payload matching Laboratory API contract
                payload = {
                    'patient_id': patient_id,
                    'patient_name': patient['patient_name'],
                    'age': int(patient['age']) if patient['age'] else 0,
                    'gender': patient['gender'],
                    'doctor': patient['doctor'],
                    'test_id': test_id,
                    'test_type': test_type,
                    'sample_type': sample_type,
                    'priority': priority,
                    'requested_date': requested_date,
                    'instructions': instructions
                }

                # 1. Send via REST API to Laboratory Portal
                lab_api = LabApiService()
                success, resp_data, error_msg, status_code = lab_api.create_test_request(payload)

                if not success:
                    flash(f"Submission rejected by Laboratory Portal: {error_msg}", 'danger')
                    patients = db.execute('SELECT patient_id, patient_name FROM patients').fetchall()
                    return render_template('create_test_request.html', patients=patients)

                # 2. Persist to Hospital SQLite only after confirmed receipt by Laboratory
                db.execute(
                    '''INSERT INTO test_requests (test_id, patient_id, patient_name, age, gender, doctor, 
                       test_type, sample_type, priority, requested_date, instructions, status, dropbox_file_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Sent to Laboratory', 'REST_API')''',
                    (test_id, patient_id, patient['patient_name'], patient['age'], patient['gender'], 
                     patient['doctor'], test_type, sample_type, priority, requested_date, instructions)
                )
                db.commit()

                flash(f'Test Request {test_id} successfully sent to Laboratory Portal via REST API.', 'success')
                return redirect(url_for('test_requests.index'))

            else:
                # Legacy Dropbox fallback
                db.execute(
                    '''INSERT INTO test_requests (test_id, patient_id, patient_name, age, gender, doctor, 
                       test_type, sample_type, priority, requested_date, instructions)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (test_id, patient_id, patient['patient_name'], patient['age'], patient['gender'], 
                     patient['doctor'], test_type, sample_type, priority, requested_date, instructions)
                )
                db.commit()

                temp_dir = os.path.join(current_app.instance_path, 'temp_requests')
                os.makedirs(temp_dir, exist_ok=True)
                csv_filename = f"test_request_{test_id}.csv"
                local_csv_path = os.path.join(temp_dir, csv_filename)

                with open(local_csv_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Patient_ID', 'Patient_Name', 'Age', 'Gender', 'Doctor', 'Test_ID', 
                                     'Test_Type', 'Sample_Type', 'Priority', 'Requested_Date', 'Instructions'])
                    writer.writerow([patient_id, patient['patient_name'], patient['age'], patient['gender'], 
                                     patient['doctor'], test_id, test_type, sample_type, priority, 
                                     requested_date, instructions])

                try:
                    dropbox_service = DropboxService()
                    dropbox_path = dropbox_service.upload_test_request(local_csv_path, test_id)
                    db.execute("UPDATE test_requests SET status = 'Sent to Laboratory', dropbox_file_path = ? WHERE test_id = ?",
                              (dropbox_path, test_id))
                    db.commit()
                    flash(f'Test Request {test_id} submitted successfully via Dropbox.', 'success')
                except Exception as e:
                    flash(f'Failed to upload to Dropbox: {str(e)}', 'danger')
                finally:
                    if os.path.exists(local_csv_path):
                        os.remove(local_csv_path)

                return redirect(url_for('test_requests.index'))

    patients = db.execute('SELECT patient_id, patient_name FROM patients').fetchall()
    return render_template('create_test_request.html', patients=patients)


@bp.route('/<test_id>')
@login_required
def details(test_id):
    db = get_db()
    req = db.execute('SELECT * FROM test_requests WHERE test_id = ?', (test_id,)).fetchone()

    if req is None:
        abort(404, f"Test Request id {test_id} doesn't exist.")

    return render_template('test_request_details.html', request=req)


@bp.route('/<test_id>/fetch-result', methods=['POST'])
@login_required
def fetch_result(test_id):
    """
    On-demand retrieval of a test result from the Laboratory REST API:
    GET /api/results/<test_id>
    """
    db = get_db()
    req = db.execute('SELECT * FROM test_requests WHERE test_id = ?', (test_id,)).fetchone()
    if req is None:
        abort(404, f"Test Request id {test_id} doesn't exist.")

    sync_service = ResultSyncService()
    synced, msg = sync_service.sync_single_result(test_id)

    if synced:
        flash(f'Laboratory result for Test {test_id} retrieved successfully!', 'success')
        return redirect(url_for('results.details', test_id=test_id))
    else:
        flash(msg, 'info')
        return redirect(url_for('test_requests.details', test_id=test_id))
