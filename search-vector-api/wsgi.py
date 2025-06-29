#!/usr/bin/env python
# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""WSGI entrypoint for the Vector Search API application.

This module serves as the production entry point for WSGI servers 
(like Gunicorn) to run the Flask application. It configures the
Python path to include the src directory and initializes the app.

Usage:
    - For development: python wsgi.py
    - For production: gunicorn wsgi:application
"""

import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)