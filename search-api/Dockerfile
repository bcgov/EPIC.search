# Use a specific version of Python slim image for reduced attack surface
FROM python:3.11-slim-bullseye

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install security updates and required packages
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create working directory and set permissions
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
WORKDIR /opt/app-root

# Install the requirements
COPY ./requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/opt/app-root/src \
    GUNICORN_TIMEOUT=300 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# MCP Server will auto-detect container environment
# No need to set MCP_SERVER_COMMAND explicitly

# Set proper permissions
RUN chown -R appuser:appuser /opt/app-root

# Switch to non-root user
USER appuser

# Expose port 8080 for the application
EXPOSE 8080

# Define the entry point for your application
ENTRYPOINT ["bash", "docker-entrypoint.sh"]