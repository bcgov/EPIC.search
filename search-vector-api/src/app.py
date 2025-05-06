"""The App Initiation file.

This module is for the initiation of the flask app.
"""

import os

from flask import Flask

from utils.config import get_named_config, VectorSettings, SearchSettings, ModelSettings


def create_app(run_mode=os.getenv("FLASK_ENV", "development")):
    """Create flask app."""
    # pylint: disable=import-outside-toplevel
    from resources import (
        API_BLUEPRINT,
        HEALTH_BLUEPRINT
    )

    # Flask app initialize
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(API_BLUEPRINT)
    app.register_blueprint(HEALTH_BLUEPRINT)

    # All configuration are in config file
    app.config.from_object(get_named_config(run_mode))
    
    # Initialize structured configuration objects
    app.vector_settings = VectorSettings(app.config)
    app.search_settings = SearchSettings(app.config)
    app.model_settings = ModelSettings(app.config)

    # Return App for run in run.py file
    return app
