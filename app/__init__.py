import logging
from pathlib import Path

from flask import Flask

from .config import Config
from .models import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from . import routes

    app.register_blueprint(routes.bp)
    app.register_blueprint(routes.api)

    with app.app_context():
        db.create_all()

    if not app.debug:
        logging.basicConfig(level=logging.INFO)

    if app.config.get("SCHEDULER_ENABLED", True) and not app.config.get("TESTING"):
        from .scheduler import init_scheduler

        init_scheduler(app)

    return app
