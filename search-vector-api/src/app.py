"""Application initialization module.

This module handles the initialization and configuration of the Flask application
for the Vector Search API. It's responsible for registering blueprints,
loading configuration settings, and initializing the structured configuration
objects that will be used throughout the application.
"""

import os

from flask import Flask

from utils.config import get_named_config, VectorSettings, SearchSettings, ModelSettings


def create_app(run_mode=os.getenv("FLASK_ENV", "development")):
    """Create and configure the Flask application.
    
    Initializes a Flask application instance with the appropriate configuration
    based on the specified run mode. Registers all necessary blueprints and
    sets up configuration objects that provide structured access to settings.
    
    Args:
        run_mode (str): The environment to run the application in.
                       Options: 'development', 'testing', 'production', 'docker'
                       Defaults to the FLASK_ENV environment variable or 'development'.
    
    Returns:
        Flask: A configured Flask application instance ready to run.
    """
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

    return app
