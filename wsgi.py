#wsgi.py is for Production only. For local development, use app.py which has the Flask development server and hot reload.
# wsgi.py is the tiny entrypoint file that exposes your Flask app to the production Gunicorn app server.
#In your setup, systemd starts Gunicorn with: gunicorn ... wsgi:app
#This tells Gunicorn to look for the 'app' object in the wsgi.py file, which is created by calling create_app() from your app package.

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
