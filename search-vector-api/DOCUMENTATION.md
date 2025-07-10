# Search Vector API Documentation

## Overview

The Search Vector API provides advanced semantic search capabilities using a modern two-stage architecture that combines document-level metadata filtering with chunk-level semantic search. Built on PostgreSQL with pgvector extension, the system offers high-performance search with comprehensive fallback mechanisms and cross-encoder re-ranking.

## Architecture

### Two-Stage Search Pipeline

The system implements an efficient two-stage search approach:

#### Stage 1: Document-Level Filtering

* Uses pre-computed document metadata (keywords, tags, headings) for fast document discovery  
* Applies project-based filtering constraints
* Identifies the most relevant documents before chunk-level search

#### Stage 2: Chunk-Level Semantic Search

* Performs semantic vector search within chunks of identified documents
* Uses pgvector for efficient similarity matching
* Maintains project filtering consistency

#### Search Fallback Strategy

* Broader semantic search across all chunks if no documents found
* Keyword-based search as final fallback
* Ensures relevant results when possible

### Components

1. **Document-Level Search**: Fast filtering using pre-computed document metadata
2. **Chunk-Level Search**: Semantic search within document chunks using vector embeddings
3. **Project Inference Service**: Intelligent project detection from natural language queries
4. **Vector Store**: Core service for vector and keyword operations with pgvector
5. **Embedding Service**: Text-to-vector conversion using sentence transformer models
6. **Keyword Extractor**: BERT-based keyword extraction from queries
7. **Tag Extractor**: Identifies tags in query text for filtering
8. **Re-Ranker**: Cross-encoder model for improved relevance scoring
9. **Search Orchestrator**: Manages the complete two-stage pipeline with fallback logic

### Configuration Structure

The application uses strongly-typed configuration classes for different aspects of the system:

1. **VectorSettings**: Configuration related to vector database and dimensions

   * `vector_table_name`: Name of the vector table in the database
   * `embedding_dimensions`: Dimensions of embedding vectors (default: 768)
   * `database_url`: PostgreSQL connection string
   * `time_partition_interval`: Time partitioning interval for the database

2. **SearchSettings**: Configuration related to search operations

   * `keyword_fetch_count`: Number of results to fetch in keyword search
   * `semantic_fetch_count`: Number of results to fetch in semantic search
   * `top_record_count`: Number of top records to return after re-ranking
   * `reranker_batch_size`: Batch size for processing document re-ranking
   * `min_relevance_score`: Minimum relevance score for re-ranked results (default: -10.0)

> **Note**: The default minimum relevance score is set to -10.0 because cross-encoder models like `cross-encoder/ms-marco-MiniLM-L-2-v2` can produce negative scores for relevant documents.

3.**ModelSettings**: Configuration related to machine learning models

* `cross_encoder_model`: Model name for the cross-encoder re-ranker
* `embedding_model_name`: Model name for semantic embeddings
* `keyword_model_name`: Model name for keyword extraction

These settings are initialized in `app.py` and accessible throughout the application via the Flask app context.

### Database Schema

The system uses PostgreSQL with pgvector extension and implements a two-table structure optimized for the two-stage search:

#### Documents Table

Pre-computed document-level metadata for fast filtering:

```sql
CREATE TABLE documents (
    document_id UUID PRIMARY KEY,
    document_keywords TEXT[], -- Pre-computed keywords for fast matching
    document_tags TEXT[],     -- Pre-computed tags for filtering  
    document_headings TEXT[], -- Document headings/sections
    project_id UUID,          -- Project association for filtering
    project_name TEXT,
    embedding VECTOR(768),    -- Document-level embedding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast document-level search
CREATE INDEX documents_keywords_idx ON documents USING GIN (document_keywords);
CREATE INDEX documents_tags_idx ON documents USING GIN (document_tags);  
CREATE INDEX documents_project_idx ON documents (project_id);
CREATE INDEX documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

#### Document Chunks Table

Individual chunks with semantic embeddings:

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,  -- Contains structured chunk metadata including:
                    -- {
                    --   "document_id": "uuid-string", 
                    --   "document_type": "string",
                    --   "document_name": "string",
                    --   "document_saved_name": "string", 
                    --   "page_number": "string",
                    --   "project_id": "string",
                    --   "project_name": "string",
                    --   "proponent_name": "string",
                    --   "s3_key": "string"
                    -- }
    embedding VECTOR(768),
    document_id UUID REFERENCES documents(document_id),
    project_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for chunk-level search
CREATE INDEX chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX chunks_content_idx ON document_chunks USING GIN (to_tsvector('simple', content));
CREATE INDEX chunks_document_idx ON document_chunks (document_id);
CREATE INDEX chunks_project_idx ON document_chunks (project_id);
```

## Search Process

The search process implements an efficient two-stage approach:

### Stage 1: Document-Level Search

1. **Query Processing**: Extract keywords and tags from the user query using BERT models
2. **Document Filtering**: Search the `documents` table using:
   * OR logic between keywords, tags, and headings for broad matching
   * Project-based filtering if specified
   * Fast array-based searches using GIN indexes
3. **Result**: List of relevant document IDs for Stage 2

### Stage 2: Chunk-Level Search

1. **Chunk Search**: Perform semantic vector search within chunks of identified documents
2. **Vector Similarity**: Use pgvector cosine similarity on chunk embeddings  
3. **Project Consistency**: Apply same project filtering as Stage 1
4. **Result**: Ranked list of relevant document chunks

### Fallback Logic

1. **Semantic Fallback**: If no documents found in Stage 1, search all chunks semantically
2. **Keyword Fallback**: If semantic search returns no results, fall back to keyword search
3. **Ensures Coverage**: Guarantees relevant results when possible

### Re-ranking and Formatting

1. **Cross-Encoder Re-ranking**: Use `cross-encoder/ms-marco-MiniLM-L-2-v2` for relevance scoring
2. **Relevance Filtering**: Filter results based on minimum relevance score (-10.0 default)
3. **Result Formatting**: Convert to final API response structure with metadata

## Key Features

### Two-Stage Search Architecture

The system's efficiency comes from its two-stage approach:

**Benefits:**

* Faster search by filtering documents before chunk search
* Better relevance by using document-level metadata
* Reduced computational overhead compared to searching all chunks
* Maintains high recall through comprehensive fallback logic

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

* Vector similarity using cosine distance
* Filtering by tags and metadata
* Time range filtering
* Customizable result limit

### Keyword Search

Keyword search uses PostgreSQL's full-text search capabilities to find documents matching extracted keywords:

```sql
SELECT id, content, metadata, ts_rank_cd(to_tsvector('simple', content), query) as rank
FROM table_name, websearch_to_tsquery('simple', %s) query
WHERE to_tsvector('simple', content) @@ query AND conditions
ORDER BY rank DESC
LIMIT limit
```

### Project-Based Filtering

All search operations support project-based filtering:

* Applied consistently across both search stages  
* Uses database indexes for efficient filtering
* Maintains search quality within project constraints

### Result Re-ranking and Advanced Relevance Scoring

After retrieving results from the two-stage search pipeline, a cross-encoder model is used to re-rank them based on relevance to the original query:

1. **Pair Formation**: The query and each document chunk are paired together
2. **Cross-Encoder Evaluation**: The `cross-encoder/ms-marco-MiniLM-L-2-v2` model evaluates each query-document pair
3. **Score Generation**: Model produces raw logit scores (can be positive or negative)
4. **Sorting**: Results are sorted by relevance scores in descending order (higher = more relevant)
5. **Filtering**: Results below the minimum relevance threshold are filtered out
6. **Top-N Selection**: Final top N results are returned to the user

#### Understanding Cross-Encoder Scores

Cross-encoder models produce **raw logit scores** with specific characteristics:

* **Can be positive OR negative** - Negative scores are normal for relevant documents
* **Higher values = more relevant** - Relative ranking matters more than absolute values
* **Raw logits, not probabilities** - Model outputs before normalization

#### Example Scores

From actual search results:

```json
{
  "relevance_score": -4.135  // Highly relevant (passes -10.0 threshold)
},
{
  "relevance_score": -6.762  // Still relevant (passes -10.0 threshold)  
}
```

These negative scores represent relevant documents that would be incorrectly filtered with a 0.0 threshold.

## API Endpoints

### Vector Search

```http
POST /api/vector-search
```

Performs the two-stage search pipeline with document-level filtering followed by chunk-level semantic search.

**Request Body:**

```json
{
  "query": "climate change impacts on wildlife",
  "project_ids": ["project-123", "project-456"]  // Optional project filtering
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
      "document_search_ms": 1715.4,     // Stage 1: Document-level search time
      "chunk_search_ms": 126.49,       // Stage 2: Chunk-level search time  
      "reranking_ms": 2659.92,         // Cross-encoder re-ranking time
      "formatting_ms": 0.0,            // Result formatting time
      "total_search_ms": 4502.32       // Total search pipeline time
    }
  }
}
```

### Document Similarity Search

```http  
POST /api/document-similarity
```

Finds documents similar to a specified document using document-level embeddings.

**Request Body:**

```json
{
  "document_id": "uuid-string",
  "project_ids": ["project-123"],  // Optional project filtering
  "limit": 10                      // Optional, default: 10
}
```

**Response:**

```json
{
  "similar_documents": [
    {
      "document_id": "similar-doc-uuid",
      "document_keywords": ["climate", "environmental", "impact"],
      "document_tags": ["Environmental", "Research"],
      "document_headings": ["Introduction", "Methodology", "Results"],
      "project_id": "project-123", 
      "similarity_score": 0.8542,
      "created_at": "2023-10-15T14:30:00Z"
    }
  ],
  "search_metrics": {
    "embedding_retrieval_ms": 25.3,
    "similarity_search_ms": 158.7,
    "formatting_ms": 2.1,
    "total_search_ms": 186.1
  }
}
```

### Intelligent Project Inference

The search system includes automatic project detection that can infer which project(s) a user is querying about based on the natural language in their query. This feature only activates when no explicit project IDs are provided and operates with high confidence thresholds to ensure accuracy.

#### How Project Inference Works

**Entity Extraction**: The system analyzes queries for:

* Project names (e.g., "Site C project", "Trans Mountain pipeline")
* Infrastructure project terms (e.g., "mine", "dam", "terminal", "facility")
* Quoted project references
* Capitalized project-specific terminology

**Project Matching**: Extracted entities are matched against known projects using:

* Fuzzy string matching for similarity scoring against project names
* Substring matching for partial project name matches  
* Confidence scoring based on project name match quality only
* Direct querying of the projects table for efficient lookup

**Query Cleaning**: After project identification, the system automatically:

* Removes identified project names from the search query
* Focuses search on actual topics rather than project names
* Prevents project name mentions from dominating search results
* Ensures relevant content is prioritized over project name references

**Automatic Application**: Project filtering is automatically applied when:

* Confidence score exceeds 80% threshold
* No explicit project IDs were provided in the request
* Clear project names are detected in the query

#### Example Queries with Automatic Project Inference

| Query | Detected Entity | Cleaned Query | Matched Project | Confidence | Applied |
|-------|----------------|---------------|----------------|------------|---------|
| "Who is the main proponent for the Site C project?" | "Site C project" | "Who is the main proponent for" | Site C Clean Energy Project | 92% | ✅ Yes |
| "Environmental impacts of Trans Mountain pipeline" | "Trans Mountain pipeline" | "Environmental impacts of" | Trans Mountain Pipeline | 92% | ✅ Yes |
| "Coyote Hydrogen project zoning and land use" | "Coyote Hydrogen project" | "zoning and land use" | Coyote Hydrogen Project | 88% | ✅ Yes |
| "impact assessment procedures" | None | "impact assessment procedures" | N/A | 0% | ❌ No |

#### API Response with Project Inference

When project inference occurs, the API response includes additional metadata:

```json
{
  "vector_search": {
    "documents": [...],
    "search_metrics": {...},
    "project_inference": {
      "attempted": true,
      "confidence": 0.92,
      "inferred_project_ids": ["proj-001"],
      "applied": true,
      "original_query": "Coyote Hydrogen project zoning and land use",
      "cleaned_query": "zoning and land use",
      "metadata": {
        "extracted_entities": ["Coyote Hydrogen project"],
        "matched_projects": [
          {
            "entity": "Coyote Hydrogen project",
            "project_id": "proj-001", 
            "project_name": "Coyote Hydrogen Project",
            "similarity": 0.92
          }
        ],
        "reasoning": ["Detected entity 'Coyote Hydrogen project' matching project 'Coyote Hydrogen Project' with similarity 0.920"]
      }
    }
  }
}
```

#### Benefits

* **User-Friendly**: No need to know specific project IDs
* **Context-Aware**: Automatically focuses search on relevant project scope
* **Performance**: Reduces search space for faster, more relevant results
* **Transparent**: Full inference metadata provided for debugging/auditing
* **Conservative**: Only applies when highly confident (>80%) to avoid false positives
* **Intelligent Query Processing**: Removes project names from search to focus on actual topics
* **Improved Relevance**: Prevents project name mentions from dominating search results

#### Model Processing

* **Batch Processing**: Configurable batch size for efficiency (default: 8)
* **Query-Document Pairs**: Each query-document combination is evaluated together
* **Ranking Focus**: Emphasizes relative score comparison over absolute values

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
| VECTOR_TABLE | Default table name for vector storage | document_chunks |

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

* Direct pgvector implementation provides efficient vector similarity search using index structures
* Search time is logged for each stage of the pipeline for performance monitoring
* For large datasets, consider:
  * Increasing the number of IVF lists in the index
  * Using approximate nearest neighbor search
  * Implementing caching for frequent queries

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

* `PRELOAD_EMBEDDING_MODEL`: Model to use for generating vector embeddings
* `PRELOAD_KEYWORD_MODEL`: Model to use for keyword extraction (typically same as embedding model)
* `PRELOAD_CROSS_ENCODER_MODEL`: Cross-encoder model for re-ranking search results

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

### Statistics API

The Stats API provides comprehensive processing statistics and metrics for document processing operations. It tracks document processing success rates, failure counts, and detailed logs by joining data from the `processing_logs` and `projects` tables.

#### Processing Statistics

```http
GET /api/stats/processing
POST /api/stats/processing
```

Retrieves aggregated processing statistics across all projects or filtered by specific project IDs.

**GET Request (All Projects):**

```http
GET /api/stats/processing
```

**POST Request (Filtered Projects):**

```json
{
  "projectIds": ["project-123", "project-456"]
}
```

**Response:**

```json
{
  "processing_stats": {
    "projects": [
      {
        "project_id": "project-123",
        "project_name": "Site C Clean Energy Project",
        "total_files": 150,
        "successful_files": 140,
        "failed_files": 10,
        "success_rate": 93.33
      }
    ],
    "summary": {
      "total_projects": 5,
      "total_files_across_all_projects": 750,
      "total_successful_files": 720,
      "total_failed_files": 30,
      "overall_success_rate": 96.0
    }
  }
}
```

#### Project Processing Details

```http
GET /api/stats/project/{project_id}
```

Provides detailed processing logs for a specific project including individual document processing records.

**Response:**

```json
{
  "project_details": {
    "project_id": "project-123",
    "project_name": "Site C Clean Energy Project",
    "processing_logs": [
      {
        "log_id": 1,
        "document_id": "environmental_assessment.pdf",
        "status": "success",
        "processed_at": "2024-01-15T10:30:00Z",
        "metrics": {
          "processing_time_ms": 1500,
          "file_size_bytes": 2048000
        }
      }
    ],
    "summary": {
      "total_files": 50,
      "successful_files": 48,
      "failed_files": 2,
      "success_rate": 96.0
    }
  }
}
```

#### Processing Summary

```http
GET /api/stats/summary
```

Provides a high-level summary of processing statistics across the entire system.

**Response:**

```json
{
  "processing_summary": {
    "total_projects": 5,
    "total_files_across_all_projects": 750,
    "total_successful_files": 720,
    "total_failed_files": 30,
    "overall_success_rate": 96.0,
    "projects_with_failures": 2,
    "avg_success_rate_per_project": 95.5
  }
}
```

#### Stats Database Requirements

The Stats API requires the following database tables:

**projects table:**

* `project_id` (String, Primary Key)
* `project_name` (VARCHAR)

**processing_logs table:**

* `id` (Integer, Primary Key)
* `project_id` (String, Foreign Key)
* `document_id` (VARCHAR)
* `status` (VARCHAR: "success" or "failure")
* `processed_at` (TIMESTAMP)
* `metrics` (JSONB)

## Future Enhancements

* Add authentication and rate limiting
* Implement caching for frequent queries
* Support for more advanced filtering options
* Vector quantization for larger datasets
* Personalized search results based on user preferences
* Support for more language models and embedding techniques
