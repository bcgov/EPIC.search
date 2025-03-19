"""The App Initiation file.

This module is for the initiation of the flask app.
"""

import os

from flask import Flask

from utils import cache

def create_app(run_mode=os.getenv("FLASK_ENV", "development")):
    """Create flask app."""
    # pylint: disable=import-outside-toplevel

    # Flask app initialize
    app = Flask(__name__)

    # All configuration are in config file
    # app.config.from_object(get_named_config(run_mode))

    # Return App for run in run.py file
    return app


def build_cache(app):
    """Build cache."""
    cache.init_app(app)
