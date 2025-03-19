# Use the python:3.9-buster image as the base image
FROM python:3.9-buster

# Create working directory
RUN mkdir /opt/app-root && chmod 755 /opt/app-root
WORKDIR /opt/app-root

# Install the requirements
COPY ./requirements/docker/requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

RUN chmod +x /opt/app-root/preload_models.py

# Set environment variables
ENV PYTHONPATH=/opt/app-root/src

ENV GUNICORN_TIMEOUT=300

# Define the entry point for your application
ENTRYPOINT ["bash", "docker-entrypoint.sh"]