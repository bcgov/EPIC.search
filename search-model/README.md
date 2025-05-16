# Search Model Development Container

This directory contains a flexible Docker container for local development and testing of the search functionality using Ollama-compatible models. The container is designed to be used in a development environment and can be configured to use different models via build arguments.

## Supported Models

The container supports any model available through Ollama. Common choices include:

- `qwen2.5:0.5b`: A lightweight model suitable for development and testing
- `qwen2.5:3b`: A medium-sized model for more accurate results
- Other Ollama-compatible models

## Development Setup

### Prerequisites

- Docker
- Docker Compose
- RAM requirements vary by model:
  - 8GB+ RAM for smaller models (0.5b)
  - 16GB+ RAM for medium models (3b)

### Quick Start

Build the container with your desired model:

```bash
# Build with specific model parameters
docker build -t search-model-dev:latest \
    --build-arg MODEL_NAME=qwen2.5 \
    --build-arg MODEL_VERSION=3b \
    .

2. Run the container:

```bash
docker run --rm -p 8000:8000 search-model-dev:0.5b
```

### Configuration

The containers expose port 8000 by default. You can configure the following environment variables:

- `MODEL_PATH`: Path to the model within the container
- `MAX_MEMORY`: Maximum memory allocation for the model

## Local Development

For local development, you can mount your local model files into the container:

```bash
docker run --rm -p 8000:8000 -v /path/to/local/models:/models search-model-dev:0.5b
```

## Notes

- These containers are optimized for development and testing purposes
- For production deployments, refer to the DOCUMENTATION.md file
