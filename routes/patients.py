from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort
from routes.auth import login_required
from database.database import get_db

bp = Blueprint('patients', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    
    # Summary stats
    stats = {}
    stats['total_patients'] = db.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
    
    req_counts = db.execute('''
        SELECT status, COUNT(*) FROM test_requests GROUP BY status
    ''').fetchall()
    
    stats['pending_tests'] = 0
    stats['in_progress'] = 0
    stats['completed'] = 0
    stats['abnormal'] = 0
    
    for row in req_counts:
        status = row[0].lower()
        if status in ['pending', 'sent to laboratory']:
            stats['pending_tests'] += row[1]
        elif status == 'processing':
            stats['in_progress'] += row[1]
        elif status == 'completed':
            stats['completed'] += row[1]
        elif status == 'abnormal':
            stats['abnormal'] += row[1]
            
    recent_patients = db.execute('SELECT * FROM patients ORDER BY created_at DESC LIMIT 5').fetchall()
    recent_requests = db.execute('SELECT * FROM test_requests ORDER BY created_at DESC LIMIT 5').fetchall()
    recent_results = db.execute('SELECT * FROM test_results ORDER BY created_at DESC LIMIT 5').fetchall()
    
    return render_template('dashboard.html', stats=stats, recent_patients=recent_patients, 
                           recent_requests=recent_requests, recent_results=recent_results)

@bp.route('/patients')
@login_required
def index():
    db = get_db()
    patients = db.execute('SELECT * FROM patients ORDER BY created_at DESC').fetchall()
    return render_template('patients.html', patients=patients)

@bp.route('/patients/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        patient_name = request.form['patient_name']
        age = request.form['age']
        gender = request.form['gender']
        date_of_birth = request.form['date_of_birth']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        emergency_contact = request.form['emergency_contact']
        doctor = request.form['doctor']
        department = request.form['department']
        
        db = get_db()
        error = None

        if not patient_id:
            error = 'Patient ID is required.'
        elif db.execute('SELECT id FROM patients WHERE patient_id = ?', (patient_id,)).fetchone() is not None:
            error = f"Patient ID {patient_id} is already registered."

        if error is not None:
            flash(error, 'danger')
        else:
            db.execute(
                '''INSERT INTO patients (patient_id, patient_name, age, gender, date_of_birth, 
                   phone, email, address, emergency_contact, doctor, department)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (patient_id, patient_name, age, gender, date_of_birth, phone, email, 
                 address, emergency_contact, doctor, department)
            )
            db.commit()
            flash('Patient registered successfully!', 'success')
            return redirect(url_for('patients.index'))

    return render_template('patient_form.html')

@bp.route('/patients/<patient_id>')
@login_required
def details(patient_id):
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE patient_id = ?', (patient_id,)).fetchone()
    
    if patient is None:
        abort(404, f"Patient id {patient_id} doesn't exist.")
        
    test_history = db.execute('SELECT * FROM test_requests WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    
    return render_template('patient_details.html', patient=patient, test_history=test_history)
