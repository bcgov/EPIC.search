import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from search_api import create_app

application = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    application.run(debug=debug_mode, host='0.0.0.0', port=8080, use_reloader=False)    