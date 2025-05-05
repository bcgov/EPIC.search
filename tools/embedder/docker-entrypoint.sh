#!/bin/bash
set -e

# Docker container entrypoint script for EPIC.search Embedder
# 
# This script serves as the entrypoint for the EPIC.search Embedder Docker container.
# It passes any arguments provided to the container directly to the Python main.py script,
# which allows for configuring the embedder through command-line arguments like --project_id.
#
# The 'set -e' ensures the script exits immediately if any command fails.

# Start the application with arguments passed to the container
echo "Starting application with arguments: $@"
exec python main.py "$@"