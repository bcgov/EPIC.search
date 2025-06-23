# Search Vector API Documentation

## Overview

The Search Vector API provides semantic vector search and keyword-based search capabilities for documents using PostgreSQL with the pgvector extension. This document outlines the architecture, components, and usage of the API.

## Architecture

### Components

1. **Vector Store**: Core service for vector and keyword-based search operations with pgvector
2. **Embedding Service**: Converts text to vector embeddings using sentence transformer models
3. **Keyword Extractor**: Extracts relevant keywords from query text using KeyBERT
4. **Tag Extractor**: Identifies tags in query text for filtering
5. **Re-Ranker**: Improves search results by re-ranking based on relevance using cross-encoder models
6. **Search Service**: Orchestrates the complete search process from query to results

### Configuration Structure

The application uses strongly-typed configuration classes for different aspects of the system:

1. **VectorSettings**: Configuration related to vector database and dimensions
   - `vector_table_name`: Name of the vector table in the database
   - `embedding_dimensions`: Dimensions of embedding vectors (default: 768)
   - `database_url`: PostgreSQL connection string
   - `time_partition_interval`: Time partitioning interval for the database

2. **SearchSettings**: Configuration related to search operations
   - `keyword_fetch_count`: Number of results to fetch in keyword search
   - `semantic_fetch_count`: Number of results to fetch in semantic search
   - `top_record_count`: Number of top records to return after re-ranking
   - `reranker_batch_size`: Batch size for processing document re-ranking
   - `min_relevance_score`: Minimum relevance score for re-ranked results (default: 0.0)

3. **ModelSettings**: Configuration related to machine learning models
   - `cross_encoder_model`: Model name for the cross-encoder re-ranker
   - `embedding_model_name`: Model name for semantic embeddings
   - `keyword_model_name`: Model name for keyword extraction

These settings are initialized in `app.py` and accessible throughout the application via the Flask app context.

### Database Schema

The system uses PostgreSQL with the pgvector extension. Each document collection is stored in a table with the following structure:

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,  -- Contains structured document metadata including:
                    -- {
                    --   "document_id": "uuid-string",
                    --   "document_type": "string",
                    --   "document_name": "string",
                    --   "document_saved_name": "string",
                    --   "page_number": number,
                    --   "project_id": "string",
                    --   "project_name": "string",
                    --   "proponent_name": "string",
                    --   "s3_key": "string"
                    -- }
    embedding VECTOR(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create index for full-text search
CREATE INDEX content_idx ON documents USING GIN (to_tsvector('simple', content));
```

## Search Pipeline

The search process follows these steps:

1. **Query Processing**: The user's query is processed to extract embeddings and keywords
2. **Parallel Search**: Both semantic (vector) and keyword searches are performed simultaneously
3. **Result Combination**: Results from both search methods are combined
4. **Deduplication**: Duplicate results are removed based on document ID
5. **Re-ranking**: Results are re-ranked using a cross-encoder model for improved relevance
6. **Formatting**: Results are formatted into a consistent structure for the API response
7. **Performance Metrics**: Search time for each step is recorded and returned

## Key Features

### Semantic Search

The semantic search functionality converts user queries to vector embeddings and finds similar documents using cosine similarity. The implementation uses pgvector's native vector similarity operators:

```sql
SELECT id, metadata, content, embedding, 1 - (embedding <=> %s::vector) as similarity
FROM table_name
WHERE conditions
ORDER BY embedding <=> %s::vector
LIMIT limit
```

Key features of semantic search:

- Vector similarity using cosine distance
- Filtering by tags and metadata
- Time range filtering
- Customizable result limit

### Keyword Search

Keyword search uses PostgreSQL's full-text search capabilities to find documents matching extracted keywords:

```sql
SELECT id, content, metadata, ts_rank_cd(to_tsvector('simple', content), query) as rank
FROM table_name, websearch_to_tsquery('simple', %s) query
WHERE to_tsvector('simple', content) @@ query AND conditions
ORDER BY rank DESC
LIMIT limit
```

### Result Re-ranking

After retrieving results from both search methods, a cross-encoder model is used to re-rank them based on relevance to the original query:

1. The query and each document are paired together
2. The cross-encoder model evaluates the relevance of each pair
3. Results are sorted based on the relevance scores
4. Top N results are returned to the user

## API Endpoints

### Search Endpoint

``` code
POST /api/vector-search
```

Request Body:

```json
{
  "query": "climate change impacts"
}
```

Response:

```json
{
  "vector_search": {
    "documents": [      {
        "document_id": "uuid-string",
        "document_type": "PDF",
        "document_name": "Climate Report",
        "document_saved_name": "climate_report_2023.pdf",
        "page_number": 42,
        "project_id": "project-123",
        "project_name": "Climate Research Initiative",
        "proponent_name": "Environmental Research Group",
        "s3_key": "documents/project-123/climate_report_2023.pdf",
        "content": "Document content extract with relevant information...",
        "relevance_score": 0.85
      }
    ],
    "search_metrics": {
      "keyword_search_ms": 52.15,
      "semantic_search_ms": 157.89,
      "combine_results_ms": 1.23,
      "deduplication_ms": 0.98,
      "reranking_ms": 235.67,
      "formatting_ms": 3.45,
      "total_search_ms": 451.37
    }
  }
}
```

## Configuration

The application uses environment variables for configuration with sensible defaults. Environment variables can be set directly or through a `.env` file in the root directory. A sample configuration is provided in the `sample.env` file.

### Environment Variables

The configuration variables are organized into logical groups:

#### Flask Application Environment

| Parameter | Description | Default |
|-----------|-------------|---------|
| FLASK_ENV | Application environment mode (development, production, testing, docker) | development |

#### Vector Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| VECTOR_DB_URL | PostgreSQL connection string | postgresql://postgres:postgres@localhost:5432/postgres |
| EMBEDDING_DIMENSIONS | Dimensions of embedding vectors | 768 |
| VECTOR_TABLE | Default table name for vector storage | document_tags |

#### Search Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| KEYWORD_FETCH_COUNT | Number of results to fetch in keyword search | 100 |
| SEMANTIC_FETCH_COUNT | Number of results to fetch in semantic search | 100 |
| TOP_RECORD_COUNT | Number of top records to return after re-ranking | 10 |
| RERANKER_BATCH_SIZE | Batch size for the cross-encoder re-ranker | 8 |
| MIN_RELEVANCE_SCORE | Minimum relevance score for re-ranked results | 0.0 |

#### ML Model Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| CROSS_ENCODER_MODEL | Model for re-ranking results | cross-encoder/ms-marco-MiniLM-L-2-v2 |
| EMBEDDING_MODEL_NAME | Model for generating embeddings | all-mpnet-base-v2 |
| KEYWORD_MODEL_NAME | Model for keyword extraction | all-mpnet-base-v2 |

### Configuration Classes

The environment variables are loaded into strongly-typed configuration classes:

```python
# Accessed in code via current_app.vector_settings.database_url
class VectorSettings:
    def __init__(self, config_dict):
        self._config = config_dict
    
    @property
    def database_url(self):
        return self._config.get("VECTOR_DB_URL")
    
    # Additional properties...
```

## Usage Examples

### Basic Search

```bash
curl -X POST "http://localhost:5000/api/vector-search" \
  -H "Content-Type: application/json" \
  -d '{"query":"climate change"}'
```

## Performance Considerations

- Direct pgvector implementation provides efficient vector similarity search using index structures
- Search time is logged for each stage of the pipeline for performance monitoring
- For large datasets, consider:
  - Increasing the number of IVF lists in the index
  - Using approximate nearest neighbor search
  - Implementing caching for frequent queries

## Implementation Notes

This solution uses pgvector directly with raw SQL queries for vector similarity search. Key features:

1. Direct SQL queries to PostgreSQL with the pgvector extension
2. Proper casting of vector types in SQL queries with `::vector` notation
3. Strongly-typed configuration with property-based access and sensible defaults
4. Performance optimizations through parameterized SQL queries
5. Comprehensive search pipeline with deduplication and re-ranking

## Development and Deployment

### Local Development

1. Create a `.env` file in the root directory with your configuration (based on `sample.env`)
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python wsgi.py`

### Docker Deployment

The application includes Docker configuration for containerized deployment:

1. Build the image: `docker build -t vector-search-api .`
2. Run the container: `docker run -p 8080:8080 --env-file .env vector-search-api`

The `docker-entrypoint.sh` script handles initialization tasks like preloading models.

#### Model Preloading

The application offers three distinct options for managing ML model loading:

1. **Build-time Preloading**: Embed models directly in the Docker image
2. **Startup Preloading**: Download models when the container starts
3. **Lazy Loading**: Download models on first use (default)

##### Option 1: Build-time Preloading

Models can be preloaded during the Docker build process to cache them in the image. This creates larger images but ensures models are always immediately available:

```bash
docker build \
  --build-arg PRELOAD_EMBEDDING_MODEL="all-mpnet-base-v2" \
  --build-arg PRELOAD_KEYWORD_MODEL="all-mpnet-base-v2" \
  --build-arg PRELOAD_CROSS_ENCODER_MODEL="cross-encoder/ms-marco-MiniLM-L-2-v2" \
  -t vector-search-api .
```

When preloading is enabled, the following must be specified:

- `PRELOAD_EMBEDDING_MODEL`: Model to use for generating vector embeddings
- `PRELOAD_KEYWORD_MODEL`: Model to use for keyword extraction (typically same as embedding model)
- `PRELOAD_CROSS_ENCODER_MODEL`: Cross-encoder model for re-ranking search results

##### Option 2: Startup Preloading

Models can be preloaded when the container starts by setting the `PRELOAD_MODELS` environment variable to `true`. This keeps your image size smaller but ensures the models are ready when the first request arrives:

```bash
# Using environment variable
docker run -p 8080:8080 -e PRELOAD_MODELS=true vector-search-api

# Or using env file
docker run -p 8080:8080 --env-file .env vector-search-api
# (where .env contains PRELOAD_MODELS=true)
```

##### Option 3: Lazy Loading (Default)

By default (`PRELOAD_MODELS=false`), models are downloaded and initialized only when they're first needed by the application. This provides the smallest image size and fastest container startup, but the first few requests that need the models will experience higher latency.

```bash
# Default behavior - no special flags needed
docker run -p 8080:8080 vector-search-api
```

Choosing the appropriate model loading strategy depends on your specific deployment needs, performance requirements, and infrastructure constraints. Build-time preloading is ideal for production deployments where response time consistency is critical, while lazy loading may be more suitable for development environments.

## Future Enhancements

- Add authentication and rate limiting
- Implement caching for frequent queries
- Support for more advanced filtering options
- Vector quantization for larger datasets
- Personalized search results based on user preferences
- Support for more language models and embedding techniques
