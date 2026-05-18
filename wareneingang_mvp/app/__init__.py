from flask import Flask
from config import Config
from app.extensions import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app import models

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        if app.config.get("AUTO_CREATE_TABLES", False):
            db.create_all()

    return app