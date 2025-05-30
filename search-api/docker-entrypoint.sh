#!/bin/bash
# Get the timeout from environment variable or default to 300 seconds
TIMEOUT=${GUNICORN_TIMEOUT:-300}
WORKERS=2
echo "Workers set : $WORKERS"
echo "Timeout set : $TIMEOUT"
# Start Gunicorn with increased timeout
echo 'Starting application'
exec gunicorn --bind 0.0.0.0:8080 --workers $WORKERS --timeout $TIMEOUT wsgi:application