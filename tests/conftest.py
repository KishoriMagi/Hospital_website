import pytest
import os
import tempfile
from app import create_app
from database.database import init_db, get_db
import sqlite3

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    mock_dir = tempfile.mkdtemp()
    mock_req_dir = os.path.join(mock_dir, 'Requests')
    mock_res_dir = os.path.join(mock_dir, 'Results')
    os.makedirs(mock_req_dir)
    os.makedirs(mock_res_dir)
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'WTF_CSRF_ENABLED': False,
        'USE_LOCAL_MOCK': True,
        'MOCK_REQUESTS_DIR': mock_req_dir,
        'MOCK_RESULTS_DIR': mock_res_dir
    })

    with app.app_context():
        init_db()

    yield app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth(client):
    class AuthActions:
        def login(self, staff_id='HOSP101', password='admin123'):
            return client.post(
                '/auth/login',
                data={'staff_id': staff_id, 'password': password}
            )

        def logout(self):
            return client.get('/auth/logout')

    return AuthActions()
