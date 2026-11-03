from app import create_app

# WSGI application entry point
app = create_app()

if __name__ == "__main__":
    app.run()
