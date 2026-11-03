import os
from flask import Flask, redirect, url_for, g, render_template
from config import Config
from database.database import init_app

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_app(app)

    # Register Blueprints
    from routes.auth import bp as auth_bp
    from routes.patients import bp as patients_bp
    from routes.test_requests import bp as requests_bp
    from routes.results import bp as results_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(results_bp)

    @app.route('/')
    def index():
        if g.user:
            return redirect(url_for('patients.dashboard'))
        return redirect(url_for('auth.login'))

    return app

# WSGI application instance for Gunicorn / Render production deployment
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, port=port)
