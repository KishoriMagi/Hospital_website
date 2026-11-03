import os
import shutil
from flask import current_app


class DropboxService:
    def __init__(self, app=None):
        self.app = app or current_app
        self.use_mock = self.app.config.get('USE_LOCAL_MOCK', True)
        if not self.use_mock:
            # Only import dropbox when actually needed (real API mode)
            try:
                import dropbox as _dropbox
                self.dbx = _dropbox.Dropbox(self.app.config['DROPBOX_ACCESS_TOKEN'])
                self._dropbox = _dropbox
            except ImportError:
                raise ImportError(
                    "The 'dropbox' package is required when USE_LOCAL_MOCK=False. "
                    "Install it with: pip install dropbox"
                )
        else:
            self.mock_req_dir = self.app.config['MOCK_REQUESTS_DIR']
            self.mock_res_dir = self.app.config['MOCK_RESULTS_DIR']
            os.makedirs(self.mock_req_dir, exist_ok=True)
            os.makedirs(self.mock_res_dir, exist_ok=True)

    def upload_test_request(self, file_path, test_id):
        filename = f"test_request_{test_id}.csv"
        dropbox_path = f"{self.app.config['DROPBOX_REQUEST_FOLDER']}/{filename}"

        if self.use_mock:
            dest_path = os.path.join(self.mock_req_dir, filename)
            shutil.copy2(file_path, dest_path)
            return dropbox_path
        else:
            with open(file_path, 'rb') as f:
                self.dbx.files_upload(
                    f.read(), dropbox_path,
                    mode=self._dropbox.files.WriteMode.overwrite
                )
            return dropbox_path

    def list_results(self):
        results = []
        if self.use_mock:
            if os.path.exists(self.mock_res_dir):
                for filename in os.listdir(self.mock_res_dir):
                    if filename.endswith('.csv'):
                        results.append(filename)
        else:
            try:
                response = self.dbx.files_list_folder(
                    self.app.config['DROPBOX_RESULT_FOLDER']
                )
                for entry in response.entries:
                    if (isinstance(entry, self._dropbox.files.FileMetadata)
                            and entry.name.endswith('.csv')):
                        results.append(entry.name)
            except (self._dropbox.exceptions.ApiError, self._dropbox.exceptions.AuthError, Exception) as e:
                # Re-raise friendly error or let service know
                raise Exception(f"Dropbox connection failed: {str(e)}")
        return results

    def download_result(self, filename, dest_path):
        if self.use_mock:
            src_path = os.path.join(self.mock_res_dir, filename)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dest_path)
                return True
            return False
        else:
            dropbox_path = f"{self.app.config['DROPBOX_RESULT_FOLDER']}/{filename}"
            try:
                self.dbx.files_download_to_file(dest_path, dropbox_path)
                return True
            except self._dropbox.exceptions.ApiError:
                return False
