# Use the python:3.12.9-bullseye image as the base image
FROM python:3.12.9-bullseye

# Create working directory
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
WORKDIR /opt/app-root

# Install the Python dependencies first (for better layer caching)
COPY ./requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

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

# Set environment variables
ENV PYTHONPATH=/opt/app-root/src

# Set default timeout for Gunicorn
ENV GUNICORN_TIMEOUT=300

# Set model preloading at startup to false by default
# Set to true to preload models when container starts
ENV PRELOAD_MODELS=false

EXPOSE 8080

# Define the entry point for your application
ENTRYPOINT ["bash", "docker-entrypoint.sh"]