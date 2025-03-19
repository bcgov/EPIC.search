import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run(debug=True, host='0.0.0.0', port=3300, use_reloader=False)