#!/bin/bash
set -e

# Start the application with arguments passed to the container
echo "Starting application with arguments: $@"
exec python main.py "$@"