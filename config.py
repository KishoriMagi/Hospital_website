import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Read secret key from environment; fallback only for local development
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_insecure_fallback_key_set_in_env'
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'hospital.db')
    
    # Diagnostic Laboratory REST API Integration
    # Mandatory requirement: Read laboratory URL from LAB_API_URL (with fallback to LAB_API_BASE_URL)
    LAB_API_URL = (os.environ.get('LAB_API_URL') or os.environ.get('LAB_API_BASE_URL') or 'http://127.0.0.1:5000').rstrip('/')
    LAB_API_BASE_URL = LAB_API_URL  # Backward compatibility alias
    
    # Server-to-server API Key authentication
    LAB_API_KEY = os.environ.get('LAB_API_KEY', '').strip()
    LAB_API_TIMEOUT = int(os.environ.get('LAB_API_TIMEOUT', '15'))
    USE_REST_API = os.environ.get('USE_REST_API', 'True').lower() in ('true', '1', 'yes')

    # Optional local mock paths (if any)
    MOCK_DROPBOX_DIR = os.environ.get('MOCK_EXCHANGE_DIR', '')
    MOCK_REQUESTS_DIR = os.path.join(MOCK_DROPBOX_DIR, 'Requests') if MOCK_DROPBOX_DIR else ''
    MOCK_RESULTS_DIR = os.path.join(MOCK_DROPBOX_DIR, 'Results') if MOCK_DROPBOX_DIR else ''
