# Use the python:3.12-slim-bullseye image as the base image
FROM python:3.12-slim-bullseye

# Create non-root user and set up directory permissions early
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser && \
    mkdir -p /opt/app-root && \
    mkdir -p /opt/app-root/cache && \
    chown -R appuser:appuser /opt/app-root && \
    chmod 755 /opt/app-root

WORKDIR /opt/app-root

# Install security updates and required packages, then clean up
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and set permissions for requirements.txt first
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf ~/.cache/pip/*

# Copy application code with correct ownership
COPY --chown=appuser:appuser . .

# Set execute permission only on specific files that need it
RUN chmod +x preload_models.py docker-entrypoint.sh

# Make the model preloader script executable
RUN chmod +x /opt/app-root/preload_models.py

# Preload models at build time if specified
# This will cache the models in the Docker image
RUN if [ -n "${PRELOAD_EMBEDDING_MODEL}" ] || [ -n "${PRELOAD_KEYWORD_MODEL}" ] || [ -n "${PRELOAD_CROSS_ENCODER_MODEL}" ]; then \
        # Handle embedding model  \
        if [ -n "${PRELOAD_EMBEDDING_MODEL}" ]; then \
            echo "Pre-loading embedding model: ${PRELOAD_EMBEDDING_MODEL} at build time"; \
            export EMBEDDING_MODEL_NAME=${PRELOAD_EMBEDDING_MODEL}; \
        else \
            echo "Error: PRELOAD_EMBEDDING_MODEL must be set when preloading models"; \
            exit 1; \
        fi; \
        # Handle keyword model \
        if [ -n "${PRELOAD_KEYWORD_MODEL}" ]; then \
            echo "Pre-loading keyword model: ${PRELOAD_KEYWORD_MODEL} at build time"; \
            export KEYWORD_MODEL_NAME=${PRELOAD_KEYWORD_MODEL}; \
        else \
            echo "Error: PRELOAD_KEYWORD_MODEL must be set when preloading models"; \
            exit 1; \
        fi; \
        # Handle cross-encoder model \
        if [ -n "${PRELOAD_CROSS_ENCODER_MODEL}" ]; then \
            echo "Pre-loading cross-encoder model: ${PRELOAD_CROSS_ENCODER_MODEL} at build time"; \
            export CROSS_ENCODER_MODEL=${PRELOAD_CROSS_ENCODER_MODEL}; \
        else \
            echo "Error: PRELOAD_CROSS_ENCODER_MODEL must be set when preloading models"; \
            exit 1; \
        fi; \
        # Run the preloader script \
        python preload_models.py; \
    else \
        echo "No models pre-loaded. Models will be downloaded at runtime when needed."; \
    fi

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/opt/app-root/src
ENV TRANSFORMERS_CACHE=/opt/app-root/cache
ENV HF_HOME=/opt/app-root/cache
ENV SENTENCE_TRANSFORMERS_HOME=/opt/app-root/cache

# Set default timeout for Gunicorn
ENV GUNICORN_TIMEOUT=300

# Set model preloading at startup to false by default
# Set to true to preload models when container starts
ENV PRELOAD_MODELS=false

EXPOSE 8080

# Define the entry point for your application
ENTRYPOINT ["bash", "docker-entrypoint.sh"]