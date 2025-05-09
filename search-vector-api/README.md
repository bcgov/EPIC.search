# VECTOR-SEARCH-API

A search Python flask API application that provides semantic and keyword-based search capabilities using pgvector.

## Features

* Semantic vector search using pgvector and sentence transformer models
* Keyword-based full-text search with PostgreSQL
* Hybrid search combining vector and keyword approaches
* Cross-encoder model re-ranking for improved relevance
* Tag filtering for narrowing search results
* Time range filtering for temporal constraints
* Detailed search performance metrics
* Strongly-typed configuration with sensible defaults

## Getting Started

### Development Environment

* Install the following:
  * [Python](https://www.python.org/) 3.8+
  * [Docker](https://www.docker.com/)
  * [Docker-Compose](https://docs.docker.com/compose/install/)

* Install Dependencies
  * Run `make setup` in the root of the project (search-api)

* Start the databases
  * Run `docker-compose up` in the root of the project (search-api)

### Database Setup

This project uses PostgreSQL with the pgvector extension for vector similarity search. Ensure your PostgreSQL instance has the pgvector extension installed:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Environment Variables

The development scripts for this application allow customization via an environment file in the root directory called `.env`. See an example of the environment variables that can be overridden in `sample.env`.

### Configuration Variables

The application uses typed configuration classes for different aspects of the system:

#### Vector Database Configuration

* `VECTOR_DB_URL`: PostgreSQL connection string (default: "postgresql://postgres:postgres@localhost:5432/postgres")
* `EMBEDDING_DIMENSIONS`: Dimensions of embedding vectors (default: 768)
* `VECTOR_TABLE`: Default table name for vector storage (default: "document_tags")

#### Search Configuration

* `KEYWORD_FETCH_COUNT`: Number of results to fetch in keyword search (default: 100)
* `SEMANTIC_FETCH_COUNT`: Number of results to fetch in semantic search (default: 100)
* `TOP_RECORD_COUNT`: Number of top records to return after re-ranking (default: 10)
* `RERANKER_BATCH_SIZE`: Batch size for the cross-encoder re-ranker (default: 8)

#### ML Model Configuration

* `CROSS_ENCODER_MODEL`: Model name for the cross-encoder re-ranker (default: "cross-encoder/ms-marco-MiniLM-L-2-v2")
* `EMBEDDING_MODEL_NAME`: Model name for semantic embeddings (default: "all-mpnet-base-v2")
* `KEYWORD_MODEL_NAME`: Model name for keyword extraction (default: "all-mpnet-base-v2")

## Project Structure

The application follows a structured layout to maintain separation of concerns:

```
search-vector-api/
├── src/                         # Main application source code
│   ├── app.py                   # Application initialization
│   ├── resources/               # REST API endpoints
│   │   ├── __init__.py          # Blueprint definitions
│   │   ├── ops.py               # Health/operations endpoints
│   │   └── search.py            # Search endpoints
│   ├── services/                # Business logic layer
│   │   ├── embedding.py         # Text to vector conversion
│   │   ├── re_ranker.py         # Result re-ranking with cross-encoder
│   │   ├── vector_search.py     # Main search orchestration
│   │   └── vector_store.py      # Database access layer
│   └── utils/                   # Utility modules
│       ├── config.py            # Configuration settings
│       └── cache.py             # Caching utilities
├── tests/                       # Test suite
├── wsgi.py                      # WSGI entrypoint
├── Dockerfile                   # Docker container definition
├── docker-entrypoint.sh         # Docker entrypoint script
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
└── sample.env                   # Example environment configuration
```

## Commands

### Development

The following commands support various development scenarios and needs.
Before running the following commands run `. venv/bin/activate` to enter into the virtual env.

>
> `make run`
>
> Runs the python application and runs database migrations.  
Open [http://localhost:5000/api](http://localhost:5000/api) to view it in the browser.
> The page will reload if you make edits.
> You will also see any lint errors in the console.
>
> `make test`
>
> Runs the application unit tests
>
> `make lint`
>
> Lints the application code.

### Deployment

The application can be deployed using Docker:

```bash
# Build the Docker image
docker build -t vector-search-api .

# Run the container
docker run -p 8080:8080 --env-file .env vector-search-api
```

When deploying to production, make sure to set appropriate environment variables or provide a production `.env` file with proper configuration values.

## Documentation

For more detailed technical documentation about the vector search implementation and API endpoints, see the [DOCUMENTATION.md](DOCUMENTATION.md) file.

## Architecture

The application follows a tiered architecture:

1. **API Layer** - REST endpoints in the resources directory
2. **Service Layer** - Business logic in the services directory
3. **Data Layer** - Vector database access in vector_store.py

## Key Components

* **Embedding Service** - Converts text queries to vector embeddings
* **Keyword Extractor** - Extracts relevant keywords from search queries
* **Vector Store** - Interface to the PostgreSQL database with pgvector
* **Search Service** - Orchestrates the complete search process
* **Re-Ranker** - Cross-encoder model for improving search result relevance

## Debugging in the Editor

### Visual Studio Code

Ensure the latest version of [VS Code](https://code.visualstudio.com) is installed.

The [`launch.json`](.vscode/launch.json) is already configured with a launch task (SEARCH-API Launch) that allows you to launch chrome in a debugging capacity and debug through code within the editor.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
