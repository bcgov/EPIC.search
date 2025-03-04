# Use the python:3.9-buster image as the base image
FROM python:3.9-buster

# Install dependencies needed for Ollama
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create working directory
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
WORKDIR /opt/app-root

# Install the requirements
COPY ./requirements/docker/requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Preload script to download models during build
COPY ./preload_models.py .
RUN python preload_models.py

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/opt/app-root/src

ENV GUNICORN_TIMEOUT=300

# Define the entry point for your application
ENTRYPOINT ["bash", "docker-entrypoint.sh"]