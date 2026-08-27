"""Flask extension instances shared across the application."""

from flask_sqlalchemy import SQLAlchemy

# The application factory initializes this instance with db.init_app(app).
db = SQLAlchemy()