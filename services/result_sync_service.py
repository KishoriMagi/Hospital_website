import os
import json
import logging
import pandas as pd
from flask import current_app
from database.database import get_db
from services.lab_api_service import LabApiService
from services.dropbox_service import DropboxService

logger = logging.getLogger(__name__)


class ResultSyncService:
    def __init__(self, app=None):
        self.app = app or current_app
        self.use_rest_api = self.app.config.get('USE_REST_API', True)
        self.lab_api_service = LabApiService(self.app)
        if not self.use_rest_api:
            self.dropbox_service = DropboxService(self.app)

    def sync_single_result(self, test_id):
        """
        Fetch result for a single test_id directly from the Laboratory REST API:
        GET /api/results/<test_id>
        Returns (success: bool, message: str)
        """
        db = get_db()
        request = db.execute("SELECT * FROM test_requests WHERE test_id = ?", (test_id,)).fetchone()
        if not request:
            return False, f"Test Request {test_id} not found in hospital records."

        success, data, err_msg, is_pending = self.lab_api_service.get_test_result(test_id)
        if not success:
            if is_pending:
                return False, f"Test {test_id} is still in progress at the Laboratory ({err_msg})."
            return False, f"Failed to retrieve result: {err_msg}"

        return self._save_api_result(db, request, data)

    def _save_api_result(self, db, request, data):
        """Helper to persist REST API result into local SQLite database."""
        test_id = request['test_id']
        patient_id = request['patient_id']
        test_type = data.get('test_type') or request['test_type']

        measurements = data.get('measurements') or data.get('parsed_data') or {}
        if isinstance(measurements, str):
            try:
                measurements = json.loads(measurements)
            except Exception:
                measurements = {}

        result_data_json = json.dumps(measurements)
        status = str(data.get('result_status', 'Completed'))
        remarks = str(data.get('remarks', ''))
        processed_date = str(data.get('processed_date', ''))
        dropbox_path = str(data.get('dropbox_file_path', 'REST_API'))

        # Check if result already exists in test_results
        existing = db.execute("SELECT id FROM test_results WHERE test_id = ?", (test_id,)).fetchone()
        if existing:
            db.execute(
                """UPDATE test_results
                   SET result_data = ?, result_status = ?, processed_date = ?, remarks = ?, dropbox_file_path = ?
                   WHERE test_id = ?""",
                (result_data_json, status, processed_date, remarks, dropbox_path, test_id)
            )
        else:
            db.execute(
                """INSERT INTO test_results
                   (test_id, patient_id, test_type, result_data, result_status, processed_date, remarks, dropbox_file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (test_id, patient_id, test_type, result_data_json, status, processed_date, remarks, dropbox_path)
            )

        new_req_status = 'Abnormal' if status.lower() == 'abnormal' else 'Completed'
        db.execute("UPDATE test_requests SET status = ? WHERE test_id = ?", (new_req_status, test_id))
        db.commit()

        return True, f"Result for Test {test_id} successfully synchronized."

    def sync_results(self):
        """
        Synchronize results from the Laboratory.
        When USE_REST_API=True: Calls Laboratory REST API endpoints.
        When USE_REST_API=False: Falls back to Dropbox file synchronization.
        """
        if self.use_rest_api:
            return self._sync_via_rest_api()
        return self._sync_via_dropbox()

    def _sync_via_rest_api(self):
        db = get_db()
        synced_count = 0
        errors = []

        # 1. Fetch all completed results available on the Laboratory API
        success, completed_list, err_msg = self.lab_api_service.get_all_completed_results()
        if not success:
            errors.append(f"Laboratory API Error: {err_msg}")

        synced_test_ids = set()

        if success and completed_list:
            for item in completed_list:
                test_id = item.get('test_id')
                if not test_id:
                    continue

                req = db.execute("SELECT * FROM test_requests WHERE test_id = ?", (test_id,)).fetchone()
                if not req:
                    continue  # Result belongs to a test not in this hospital instance

                # Check if already synced
                existing = db.execute("SELECT id FROM test_results WHERE test_id = ?", (test_id,)).fetchone()
                if existing:
                    continue

                saved, msg = self._save_api_result(db, req, item)
                if saved:
                    synced_count += 1
                    synced_test_ids.add(test_id)
                else:
                    errors.append(msg)

        # 2. Also check any local pending test requests via individual GET /api/results/<test_id>
        pending_requests = db.execute(
            """SELECT * FROM test_requests
               WHERE status IN ('Sent to Laboratory', 'Pending', 'Processing')"""
        ).fetchall()

        for req in pending_requests:
            test_id = req['test_id']
            if test_id in synced_test_ids:
                continue

            saved, msg = self.sync_single_result(test_id)
            if saved:
                synced_count += 1
                synced_test_ids.add(test_id)

        return synced_count, errors

    def _sync_via_dropbox(self):
        db = get_db()
        synced_count = 0
        errors = []
        try:
            files = self.dropbox_service.list_results()
        except Exception as e:
            errors.append(f"Dropbox Error: {str(e)}")
            return 0, errors

        temp_dir = os.path.join(current_app.instance_path, 'temp_results')
        os.makedirs(temp_dir, exist_ok=True)

        for filename in files:
            if not filename.startswith('test_result_') or not filename.endswith('.csv'):
                continue

            test_id = filename.replace('test_result_', '').replace('.csv', '')
            existing = db.execute("SELECT id FROM test_results WHERE test_id = ?", (test_id,)).fetchone()
            if existing:
                continue

            local_path = os.path.join(temp_dir, filename)
            if not self.dropbox_service.download_result(filename, local_path):
                errors.append(f"Failed to download {filename}")
                continue

            try:
                df = pd.read_csv(local_path)
                if df.empty:
                    errors.append(f"File {filename} is empty")
                    continue

                row = df.iloc[0]
                req_cols = ['Patient_ID', 'Test_ID', 'Test_Type', 'Result_Status', 'Processed_Date']
                missing_cols = [c for c in req_cols if c not in df.columns]
                if missing_cols:
                    errors.append(f"Missing columns in {filename}: {', '.join(missing_cols)}")
                    continue

                file_test_id = str(row['Test_ID'])
                patient_id = str(row['Patient_ID'])

                if file_test_id != test_id:
                    errors.append(f"Test ID mismatch in {filename}")
                    continue

                request = db.execute("SELECT * FROM test_requests WHERE test_id = ?", (test_id,)).fetchone()
                if not request:
                    errors.append(f"Unknown Test ID {test_id} in {filename}")
                    continue

                if request['patient_id'] != patient_id:
                    errors.append(f"Patient ID mismatch for Test {test_id} in {filename}")
                    continue

                excluded_cols = ['Patient_ID', 'Test_ID', 'Test_Type', 'Result_Status', 'Processed_Date', 'Remarks']
                measurements = {col: str(row[col]) for col in df.columns if col not in excluded_cols}
                result_data_json = json.dumps(measurements)

                status = str(row.get('Result_Status', 'Completed'))
                remarks = str(row.get('Remarks', ''))
                processed_date = str(row.get('Processed_Date', ''))
                dropbox_path = f"{current_app.config['DROPBOX_RESULT_FOLDER']}/{filename}"

                db.execute(
                    """INSERT INTO test_results (test_id, patient_id, test_type, result_data, result_status, processed_date, remarks, dropbox_file_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (test_id, patient_id, request['test_type'], result_data_json, status, processed_date, remarks, dropbox_path)
                )

                new_req_status = 'Abnormal' if status.lower() == 'abnormal' else 'Completed'
                db.execute("UPDATE test_requests SET status = ? WHERE test_id = ?", (new_req_status, test_id))
                db.commit()

                synced_count += 1

            except Exception as e:
                errors.append(f"Error processing {filename}: {str(e)}")
            finally:
                if os.path.exists(local_path):
                    os.remove(local_path)

        return synced_count, errors
