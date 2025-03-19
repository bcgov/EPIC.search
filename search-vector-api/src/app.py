"""The App Initiation file.

This module is for the initiation of the flask app.
"""

import os

from flask import Flask

from utils.config import get_named_config


def create_app(run_mode=os.getenv("FLASK_ENV", "development")):
    """Create flask app."""
    # pylint: disable=import-outside-toplevel
    from resources import (
        API_BLUEPRINT,
    )

    # Flask app initialize
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(API_BLUEPRINT)

    # All configuration are in config file
    app.config.from_object(get_named_config(run_mode))

    # Return App for run in run.py file
    return app
