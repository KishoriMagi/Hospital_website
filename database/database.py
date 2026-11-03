import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash
import os

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    
    # Create tables
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE NOT NULL,
            patient_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            date_of_birth DATE,
            phone TEXT,
            email TEXT,
            address TEXT,
            emergency_contact TEXT,
            doctor TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS test_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT UNIQUE NOT NULL,
            patient_id TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            doctor TEXT,
            test_type TEXT NOT NULL,
            sample_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            requested_date DATE NOT NULL,
            instructions TEXT,
            status TEXT DEFAULT 'Pending',
            dropbox_file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id TEXT UNIQUE NOT NULL,
            patient_id TEXT NOT NULL,
            test_type TEXT,
            result_data TEXT,
            result_status TEXT,
            processed_date DATE,
            remarks TEXT,
            dropbox_file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (test_id) REFERENCES test_requests (test_id),
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        );
    ''')

    # Create demo user if it doesn't exist
    demo_user = db.execute("SELECT * FROM users WHERE staff_id = 'HOSP101'").fetchone()
    if not demo_user:
        db.execute(
            "INSERT INTO users (staff_id, password_hash, name, role) VALUES (?, ?, ?, ?)",
            ('HOSP101', generate_password_hash('admin123'), 'Demo Staff', 'admin')
        )
        db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    with app.app_context():
        init_db()
