import json
from flask import Blueprint, flash, redirect, render_template, url_for
from werkzeug.exceptions import abort
from routes.auth import login_required
from database.database import get_db
from services.result_sync_service import ResultSyncService

bp = Blueprint('results', __name__, url_prefix='/results')

@bp.route('/')
@login_required
def index():
    db = get_db()
    
    query = '''
        SELECT tr.*, p.patient_name 
        FROM test_results tr
        JOIN patients p ON tr.patient_id = p.patient_id
        ORDER BY tr.created_at DESC
    '''
    results = db.execute(query).fetchall()
    return render_template('results.html', results=results)

@bp.route('/sync', methods=['POST'])
@login_required
def sync():
    sync_service = ResultSyncService()
    count, errors = sync_service.sync_results()
    
    if count > 0:
        flash(f'Successfully synchronized {count} results from laboratory.', 'success')
    else:
        flash('No new results found.', 'info')
        
    for error in errors:
        flash(error, 'danger')
        
    return redirect(url_for('results.index'))

@bp.route('/<test_id>')
@login_required
def details(test_id):
    db = get_db()
    result = db.execute('''
        SELECT tr.*, p.patient_name, req.sample_type, req.requested_date 
        FROM test_results tr
        JOIN patients p ON tr.patient_id = p.patient_id
        JOIN test_requests req ON tr.test_id = req.test_id
        WHERE tr.test_id = ?
    ''', (test_id,)).fetchone()
    
    if result is None:
        abort(404, f"Result for Test id {test_id} doesn't exist.")
        
    try:
        measurements = json.loads(result['result_data'])
    except:
        measurements = {}
        
    return render_template('result_details.html', result=result, measurements=measurements)
