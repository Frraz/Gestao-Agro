from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    # ... configurações ...
    db.init_app(app)
    # ... registra blueprints etc ...
    return app

__all__ = ["db"]