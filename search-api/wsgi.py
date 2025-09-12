import sys
import os
import logging

# Configure logging to match Vector API
logging.basicConfig(level=logging.INFO)

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from search_api import create_app

application = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    port = int(os.environ.get('PORT', 8081))
    application.run(debug=debug_mode, host='0.0.0.0', port=port, use_reloader=False)    