# VECTOR-SEARCH-API

A high-performance semantic search Python Flask API that provides document-level and chunk-level search capabilities using pgvector and advanced ML models.

## Features

* **Two-Stage Search Architecture**: Efficient document-level filtering followed by chunk-level semantic search
* **Document-Level Metadata Search**: Pre-computed keywords, tags, and headings for fast document discovery
* **Semantic Vector Search**: Uses pgvector and sentence transformer models for semantic similarity
* **Keyword-Based Search**: PostgreSQL full-text search with fallback capabilities
* **Cross-Encoder Re-ranking**: Advanced relevance scoring using cross-encoder models
* **Project-Based Filtering**: Filter search results by specific projects
* **Multi-Level Fallback Logic**: Ensures relevant results are always returned when possible
* **Document Similarity Search**: Find documents similar to a given document using embeddings
* **Comprehensive Performance Metrics**: Detailed timing for each search stage
* **Strongly-Typed Configuration**: Type-safe configuration with sensible defaults
* **Optional Model Preloading**: Configure model loading at build-time, startup, or on-demand

## Architecture Overview

The search system uses a modern two-stage approach:

1. **Stage 1: Document-Level Filtering** - Quickly identifies relevant documents using pre-computed metadata (keywords, tags, headings)
2. **Stage 2: Chunk-Level Search** - Performs semantic search within chunks of the identified documents
3. **Fallback Logic** - Falls back to broader search if no documents are found
4. **Re-ranking** - Uses cross-encoder models to improve result relevance
5. **Project Filtering** - Applies project-based constraints throughout the pipeline

This approach is much more efficient than searching all chunks and provides better relevance by first identifying the most promising documents.

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
* `VECTOR_TABLE`: Default table name for vector storage (default: "document_chunks")

#### Search Configuration

* `KEYWORD_FETCH_COUNT`: Number of results to fetch in keyword search (default: 100)
* `SEMANTIC_FETCH_COUNT`: Number of results to fetch in semantic search (default: 100)
* `TOP_RECORD_COUNT`: Number of top records to return after re-ranking (default: 10)
* `RERANKER_BATCH_SIZE`: Batch size for the cross-encoder re-ranker (default: 8)
* `MIN_RELEVANCE_SCORE`: Minimum relevance score for re-ranked results (default: -10.0)

> **Note**: The `MIN_RELEVANCE_SCORE` is set to -10.0 by default because cross-encoder models like `cross-encoder/ms-marco-MiniLM-L-2-v2` can produce negative relevance scores for relevant documents. This threshold ensures relevant results are not filtered out.

#### ML Model Configuration

* `CROSS_ENCODER_MODEL`: Model name for the cross-encoder re-ranker (default: "cross-encoder/ms-marco-MiniLM-L-2-v2")
* `EMBEDDING_MODEL_NAME`: Model name for semantic embeddings (default: "all-mpnet-base-v2")
* `KEYWORD_MODEL_NAME`: Model name for keyword extraction (default: "all-mpnet-base-v2")
* `PRELOAD_MODELS`: Whether to preload ML models at container startup (default: false)

## Project Structure

The application follows a structured layout to maintain separation of concerns:

```filestructure
search-vector-api/
├── src/                         # Main application source code
│   ├── app.py                   # Application initialization and configuration
│   ├── resources/               # REST API endpoints
│   │   ├── __init__.py          # Blueprint definitions
│   │   ├── apihelper.py         # API helper utilities
│   │   ├── ops.py               # Health/operations endpoints
│   │   └── search.py            # Search endpoints
│   ├── services/                # Business logic layer
│   │   ├── bert_keyword_extractor.py  # Keyword extraction using BERT
│   │   ├── embedding.py         # Text to vector conversion
│   │   ├── re_ranker.py         # Result re-ranking with cross-encoder
│   │   ├── search_service.py    # Legacy search service
│   │   ├── tag_extractor.py     # Tag extraction from queries
│   │   ├── vector_search.py     # Main search orchestration (two-stage pipeline)
│   │   └── vector_store.py      # Database access layer with pgvector
│   └── utils/                   # Utility modules
│       ├── config.py            # Strongly-typed configuration settings
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

* **Two-Stage Search Pipeline** - Document-level filtering followed by chunk-level search
* **Document-Level Search** - Uses pre-computed keywords, tags, and headings for fast document discovery
* **Embedding Service** - Converts text queries to vector embeddings using sentence transformers
* **Keyword Extractor** - Extracts relevant keywords from search queries using BERT models
* **Tag Extractor** - Identifies and extracts tags from query text for filtering
* **Vector Store** - Interface to PostgreSQL database with pgvector for both documents and chunks
* **Search Service** - Orchestrates the complete two-stage search process with fallback logic
* **Re-Ranker** - Cross-encoder model for improving search result relevance
* **Project Filtering** - Applies project-based constraints throughout the search pipeline

## Search Pipeline Stages

### Stage 1: Document-Level Search
1. Extract keywords and tags from the user query
2. Search the `documents` table using pre-computed metadata
3. Apply project-based filtering if specified
4. Return a list of relevant document IDs

### Stage 2: Chunk-Level Search
1. Search chunks within the documents identified in Stage 1
2. Use semantic vector similarity for relevance ranking
3. Apply the same project filtering for consistency

### Fallback Logic
1. If no documents are found in Stage 1, perform a broader semantic search across all chunks
2. If semantic search returns no results, fall back to keyword-based search
3. Ensures that relevant results are returned when possible

### Re-ranking and Formatting
1. Re-rank all results using a cross-encoder model for improved relevance
2. Filter results based on minimum relevance score threshold
3. Format results into the final API response structure

## Debugging in the Editor

### Visual Studio Code

Ensure the latest version of [VS Code](https://code.visualstudio.com) is installed.

The [`launch.json`](.vscode/launch.json) is already configured with a launch task (SEARCH-API Launch) that allows you to launch chrome in a debugging capacity and debug through code within the editor.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## API Response Changes

Each document in the API response now includes a `relevance_score` field, which represents the cross-encoder's confidence in the document's relevance to the query. This allows clients to further filter or sort results as needed.

**relevance_score**: Each document in the API response includes a `relevance_score` field. This is a float value produced by the cross-encoder model, representing the model's confidence in the document's relevance to the query. 

For the `cross-encoder/ms-marco-MiniLM-L-2-v2` model used by default:
- Higher values indicate greater relevance
- Scores can be negative for relevant documents (this is normal behavior)
- The minimum relevance threshold is set to -10.0 to accommodate this score range
- Scores are used for both filtering and sorting results

## API Endpoints

### Vector Search
```
POST /api/vector-search
```

Performs the two-stage search pipeline with document-level filtering followed by chunk-level semantic search.

**Request Body:**
```json
{
  "query": "climate change impacts on wildlife",
  "project_ids": ["project-123", "project-456"]  // Optional
}
```

**Response:**
```json
{
  "vector_search": {
    "documents": [
      {
        "document_id": "uuid-string",
        "document_type": "PDF", 
        "document_name": "wildlife_study.pdf",
        "document_saved_name": "Climate Impact on Wildlife 2023.pdf",
        "page_number": "15",
        "project_id": "project-123",
        "project_name": "Climate Research Initiative", 
        "proponent_name": "Environmental Research Group",
        "s3_key": "project-123/documents/wildlife_study.pdf",
        "content": "Document chunk content with relevant information...",
        "relevance_score": -4.15
      }
    ],
    "search_metrics": {
      "document_search_ms": 1715.4,
      "chunk_search_ms": 126.49, 
      "reranking_ms": 2659.92,
      "formatting_ms": 0.0,
      "total_search_ms": 4502.32
    }
  }
}
```

### Document Similarity Search
```
POST /api/document-similarity
```

Finds documents similar to a specified document using document-level embeddings.

**Request Body:**
```json
{
  "document_id": "uuid-string",
  "project_ids": ["project-123"],  // Optional
  "limit": 10  // Optional, default: 10
}
```
