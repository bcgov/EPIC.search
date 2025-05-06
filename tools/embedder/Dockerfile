# EPIC.search Embedder Dockerfile
#
# This Dockerfile builds an image for the EPIC.search Embedder application,
# which processes documents and creates vector embeddings for semantic search.
#
# The image is based on Python 3.12.9 on Debian Bullseye for stability and security.

# Use the python:3.12.9-bullseye image as the base image
FROM python:3.12.9-bullseye

# Define build-time arguments for model preloading
ARG PRELOAD_EMBEDDING_MODEL=""
ARG PRELOAD_KEYWORD_MODEL=""

# Create working directory with appropriate permissions
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
WORKDIR /opt/app-root

# Install the Python dependencies first (for better layer caching)
COPY ./requirements.txt .

# Update pip to the latest version
RUN pip install --upgrade pip

# Install dependencies without caching to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the model preloader script executable
RUN chmod +x /opt/app-root/preload_models.py

# Preload models at build time if specified
# This will cache the models in the Docker image
RUN if [ -n "${PRELOAD_EMBEDDING_MODEL}" ] || [ -n "${PRELOAD_KEYWORD_MODEL}" ]; then \
        # Handle embedding model  \
        if [ -n "${PRELOAD_EMBEDDING_MODEL}" ]; then \
            echo "Pre-loading embedding model: ${PRELOAD_EMBEDDING_MODEL} at build time"; \
            export EMBEDDING_MODEL_NAME=${PRELOAD_EMBEDDING_MODEL}; \
        fi; \
        # Handle keyword model \
        if [ -n "${PRELOAD_KEYWORD_MODEL}" ]; then \
            echo "Pre-loading keyword model: ${PRELOAD_KEYWORD_MODEL} at build time"; \
            export KEYWORD_MODEL_NAME=${PRELOAD_KEYWORD_MODEL}; \
        fi; \
        # Run the preloader script \
        python preload_models.py; \
    else \
        echo "No models pre-loaded. Models will be downloaded at runtime when needed."; \
    fi

# Set Python path to include the src directory for proper imports
ENV PYTHONPATH=/opt/app-root/src

# Expose port 8080 for potential API access
EXPOSE 8080

# Define the entry point for the application
# This uses the docker-entrypoint.sh script to handle startup and arguments
ENTRYPOINT ["bash", "docker-entrypoint.sh"]