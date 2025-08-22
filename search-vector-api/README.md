# VECTOR-SEARCH-API

A high-performance hybrid search Python Flask API that provides document-level and chunk-level search capabilities using pgvector and advanced ML models.

## Features

* **Hybrid Search Architecture**: Efficient document-level keyword filtering followed by chunk-level semantic search
* **Document-Level Keyword Filtering**: Pre-computed keywords, tags, and headings for fast document discovery using PostgreSQL full-text search
* **Semantic Vector Search**: Uses pgvector and sentence transformer models for semantic similarity within relevant documents
* **Multi-Level Fallback Strategy**: Keyword-based search fallbacks when semantic approaches don't find results
* **Cross-Encoder Re-ranking**: Advanced relevance scoring using cross-encoder models
* **Smart Query-Document Mismatch Detection**: Automatically detects and flags queries that don't match document content well
* **Intelligent Project Inference**: Automatically detects project references in queries based on project names, applies filtering when highly confident, and removes project names from the search to focus on actual topics
* **Intelligent Relevance Filtering**: Optimized thresholds to filter irrelevant results while preserving relevant documents
* **Project-Based Filtering**: Filter search results by specific projects
* **Multi-Level Fallback Logic**: Ensures relevant results are always returned when possible
* **Document Similarity Search**: Find documents similar to a given document using embeddings
* **Processing Statistics Service**: Comprehensive statistics about document processing success/failure rates by project
* **Comprehensive Performance Metrics**: Detailed timing for each search stage
* **User-Friendly Messaging**: Clear feedback when queries may need refinement
* **Strongly-Typed Configuration**: Type-safe configuration with sensible defaults
* **Optional Model Preloading**: Configure model loading at build-time, startup, or on-demand
* **Inference Control**: Optional control over which inference pipelines (PROJECT, DOCUMENTTYPE) are executed per request
* **Ranking Configuration**: Configurable relevance score thresholds and result limits with per-request overrides

## Architecture Overview

The search system uses a modern hybrid multi-stage approach with intelligent project and document type detection:

0. **Stage 0: Inference Pipeline** - Automatically detects project and document type references in natural language queries, applies filtering when highly confident, and removes detected entities from search terms to focus on actual topics
1. **Stage 1: Document-Level Keyword Filtering** - Quickly identifies relevant documents using pre-computed metadata (keywords, tags, headings) with PostgreSQL full-text search
2. **Stage 2: Chunk-Level Semantic Search** - Performs semantic search within chunks of the identified documents
3. **Fallback Logic** - Falls back to broader semantic search across all chunks, then keyword search on chunks as final fallback
4. **Re-ranking** - Uses cross-encoder models to improve result relevance
5. **Quality Assessment** - Detects low-confidence results and provides user feedback
6. **Project Filtering** - Applies project-based constraints throughout the pipeline

This hybrid approach is much more efficient than searching all chunks and provides better relevance by first identifying the most promising documents through keyword filtering, then applying expensive semantic search only to relevant content.

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
* `MIN_RELEVANCE_SCORE`: Minimum relevance score for re-ranked results (default: -8.0)

> **Note**: The `MIN_RELEVANCE_SCORE` has been optimized to -8.0 to provide better filtering of irrelevant results while preserving relevant documents. Cross-encoder models like `cross-encoder/ms-marco-MiniLM-L-2-v2` can produce negative relevance scores for relevant documents, so positive thresholds would filter out good matches. The system also includes intelligent detection of queries that don't match the document content well (all scores below -9.0), providing user feedback for potential query refinement.

#### Keyword Extraction Configuration

* `DOCUMENT_KEYWORD_EXTRACTION_METHOD`: Method used for document keyword extraction (default: "standard")
  * **"standard"**: Semantic embeddings-based extraction using KeyBERT with high-quality settings (best quality, ngrams 1-3, MMR enabled, diversity 0.8)
  * **"fast"**: Semantic embeddings-based extraction using KeyBERT with optimized settings (faster, ngrams 1-2, MMR disabled for speed)
  * **"simplified"**: Enhanced TF-IDF statistical extraction with domain-specific filtering (fastest, matches embedder implementation)
  * **⚠️ CRITICAL**: This setting **MUST** match your embedder's keyword extraction method for optimal search results

> **🎯 Perfect Alignment Required**: The API's keyword extraction implementations are precisely engineered to match the embedder processing methods. **Query keywords must be extracted using the exact same method that was used to embed the documents.** Mismatched extraction methods will result in poor search relevance because the query keywords won't align with how document keywords were originally processed. All modes include comprehensive domain-specific stopword filtering (50+ environmental assessment terms) to ensure consistency.

> **Configuration Validation**: Always verify that your search API's `DOCUMENT_KEYWORD_EXTRACTION_METHOD` matches your embedder's keyword extraction configuration. The three modes (standard/fast/simplified) use identical algorithms, parameters, and filtering to guarantee query-document keyword compatibility.

#### Search Strategy Configuration

The API supports multiple configurable search strategies to optimize for different use cases:

* `DEFAULT_SEARCH_STRATEGY`: Default search strategy when none specified in requests (default: "HYBRID_SEMANTIC_FALLBACK")

**Available Search Strategies:**

* **HYBRID_SEMANTIC_FALLBACK** (default): Document keyword filter → Semantic search → Keyword fallback
  * Filters documents using pre-computed keywords/tags, then semantic search within relevant chunks
  * Falls back to semantic search across all chunks, then keyword search if needed
  * Optimal balance of efficiency and accuracy for most queries

* **HYBRID_KEYWORD_FALLBACK**: Document keyword filter → Keyword search → Semantic fallback  
  * Filters documents using keywords/tags, then keyword search within relevant chunks
  * Falls back to keyword search across all chunks, then semantic search if needed
  * Better for queries with specific terms or technical vocabulary

* **SEMANTIC_ONLY**: Pure semantic search without keyword filtering or fallbacks
  * Direct semantic search across all chunks using embeddings
  * Best for conceptual queries where exact keyword matches aren't important
  * **Note**: More computationally expensive but finds conceptually similar content

* **KEYWORD_ONLY**: Pure keyword search without semantic components
  * Direct keyword search across all chunks using full-text search
  * Fastest option, best for exact term matching
  * **Note**: May return no results if query terms don't exactly match document content

* **HYBRID_PARALLEL**: Run semantic and keyword searches simultaneously and merge results
  * Executes both semantic and keyword searches in parallel threads
  * Merges and deduplicates results, then re-ranks combined set
  * Comprehensive coverage but higher computational cost

* **DOCUMENT_ONLY**: Direct document-level search without chunk analysis
  * Returns document-level results based on metadata filtering only
  * Automatically used for generic document requests (e.g., "show me all letters")
  * Fastest option for document browsing and type-based filtering
  * No semantic analysis or relevance scoring applied
  * **Smart Override**: When explicitly requested but the query requires content search, the system will automatically fall back to appropriate semantic/hybrid strategies for better results

The search strategy can be overridden per-request using the `searchStrategy` parameter:

```json
{
  "query": "environmental assessment",
  "searchStrategy": "SEMANTIC_ONLY"
}
```

**Important**: The `DOCUMENT_ONLY` strategy includes intelligent behavior that will automatically fall back to semantic search when the query requires content analysis rather than document browsing:

```json
// ✅ DOCUMENT_ONLY will be used - generic document request
{
  "query": "show me all correspondence letters",
  "searchStrategy": "DOCUMENT_ONLY"
}

// ❌ DOCUMENT_ONLY will be overridden - content-specific query
{
  "query": "What are the projected greenhouse gas emissions?",
  "searchStrategy": "DOCUMENT_ONLY"
}
// → System automatically uses HYBRID_SEMANTIC_FALLBACK instead
```

This intelligent override ensures optimal results regardless of the specified strategy.

#### Strategy Override Behavior

The search system includes intelligent strategy selection that can override explicitly requested strategies when they would produce suboptimal results:

**DOCUMENT_ONLY Strategy Overrides:**

* **When it works**: Generic document browsing queries ("show me all letters", "find correspondence", "list reports")
* **When it's overridden**: Content-specific queries ("What are the emissions?", "How does the process work?", "Tell me about safety concerns")
* **Override behavior**: Automatically falls back to `HYBRID_SEMANTIC_FALLBACK` for content-specific queries

**Why this happens**: `DOCUMENT_ONLY` returns document-level metadata without content analysis. For queries seeking specific information within documents, semantic search provides much better results.

**Response indicators**: Check the `strategy_metrics` in the response to see if your requested strategy was overridden:

```json
{
  "strategy_metrics": {
    "search_strategy": "HYBRID_SEMANTIC_FALLBACK",
    "strategy_applied": "HYBRID_SEMANTIC_FALLBACK", 
    "strategy_source": "intelligent_override"  // Instead of "user_requested"
  }
}
```

#### Strategy Selection Guidance

Different search strategies are optimized for different types of queries:

**Use `HYBRID_SEMANTIC_FALLBACK` (default) when:**

* You want the best balance of performance and accuracy
* Your query might contain both specific terms and conceptual language
* You're not sure which approach will work best

**Use `SEMANTIC_ONLY` when:**

* Your query is conceptual ("information about emissions")
* You want to find similar concepts even without exact word matches
* Keyword search returns no results due to vocabulary mismatch

**Use `KEYWORD_ONLY` when:**

* You're searching for exact terms or phrases
* Your query uses the same vocabulary as the documents
* You need the fastest possible search performance

**Use `HYBRID_PARALLEL` when:**

* You need the most comprehensive coverage
* Performance is less important than completeness
* You want results from both keyword and semantic approaches

**Common Issues:**

* `KEYWORD_ONLY` may return no results if your query language doesn't match document vocabulary
* `SEMANTIC_ONLY` is slower but finds conceptually similar content
* Hybrid strategies provide the best of both worlds with fallback logic

**Recent Fix:** Automatic tag filtering has been disabled in semantic search to prevent overly restrictive results. Previously, SEMANTIC_ONLY could return no results if the system detected tags in the query (like "GHG" from "greenhouse gas emissions") that didn't exist in document metadata, while HYBRID_SEMANTIC_FALLBACK would work because it uses document-level search first.

#### Ranking Configuration

* `MIN_RELEVANCE_SCORE`: Global minimum relevance score threshold for filtering results (default: -8.0)
* `TOP_RECORD_COUNT`: Global maximum number of results to return after ranking (default: 10)

These can be overridden per-request using the `ranking` object in API requests:

```json
{
  "query": "environmental assessment",
  "ranking": {
    "minScore": -6.0,    // Override minimum relevance score
    "topN": 15           // Override maximum result count
  }
}
```

#### ML Model Configuration

* `CROSS_ENCODER_MODEL`: Model name for the cross-encoder re-ranker (default: "cross-encoder/ms-marco-MiniLM-L-2-v2")
* `EMBEDDING_MODEL_NAME`: Model name for semantic embeddings (default: "all-mpnet-base-v2")
* `KEYWORD_MODEL_NAME`: Model name for keyword extraction (default: "all-mpnet-base-v2")
* `PRELOAD_MODELS`: Whether to preload ML models at container startup (default: false)

#### Inference Control Configuration

* `USE_DEFAULT_INFERENCE`: Whether to enable all inference pipelines by default when no `inference` parameter is provided in API requests (default: true)

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
│   │   ├── keyword_extractor.py     # Main keyword extraction interface
│   │   ├── keywords/            # Modular keyword extraction strategies
│   │   │   ├── simplified_query_keywords_extractor.py  # Basic word frequency
│   │   │   ├── fast_query_keywords_extractor.py        # TF-IDF based
│   │   │   └── standard_query_keywords_extractor.py    # KeyBERT semantic
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
* **Inference Pipeline** - Intelligent project and document type detection with configurable control

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

* Higher values indicate greater relevance
* Scores can be negative for relevant documents (this is normal behavior)
* The minimum relevance threshold is set to -10.0 to accommodate this score range
* Scores are used for both filtering and sorting results

## Inference Control

The API supports optional control over which inference pipelines are executed for each request:

### Available Inference Types

* **PROJECT**: Automatically detects project references in queries and applies project filtering
* **DOCUMENTTYPE**: Automatically detects document type references and applies document type filtering

### Configuration

Use the `USE_DEFAULT_INFERENCE` environment variable to control the default behavior:

* `USE_DEFAULT_INFERENCE=true` (default): Enable all inference pipelines when no `inference` parameter is provided
* `USE_DEFAULT_INFERENCE=false`: Disable all inference pipelines when no `inference` parameter is provided

### Request-Level Control

Use the optional `inference` parameter in API requests to control which inference pipelines run:

```json
{
  "query": "your search query",
  "inference": ["PROJECT", "DOCUMENTTYPE"],  // Optional: specify which pipelines to run
  "ranking": {                               // Optional: configure result filtering/limiting
    "minScore": -6.0,
    "topN": 10
  }
}
```

**Behavior:**

* `inference: ["PROJECT"]` - Only project inference runs
* `inference: ["DOCUMENTTYPE"]` - Only document type inference runs  
* `inference: ["PROJECT", "DOCUMENTTYPE"]` - Both pipelines run
* `inference: []` - No inference pipelines run
* `inference: null` or not provided - Uses `USE_DEFAULT_INFERENCE` setting

**Automatic Skipping:** Even when inference is enabled, it will be automatically skipped if explicit IDs are already provided (e.g., if you specify `project_ids` in your request, project inference will be skipped as it's not needed).

## API Endpoints

### Vector Search

``` API
POST /api/vector-search
```

Performs the two-stage search pipeline with document-level filtering followed by chunk-level semantic search.

**Request Body:**

``` json
{
  "query": "climate change impacts on wildlife",
  "projectIds": ["project-123", "project-456"],    // Optional project filtering
  "documentTypeIds": ["doc-type-123"],             // Optional document type filtering
  "inference": ["PROJECT", "DOCUMENTTYPE"],        // Optional inference control
  "ranking": {                                     // Optional ranking configuration
    "minScore": -6.0,
    "topN": 15
  }
}
```

**Response:**

``` json
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
    },
    "inference_settings": {
      "use_default_inference": true,
      "inference_parameter": ["PROJECT", "DOCUMENTTYPE"],
      "project_inference_enabled": true,
      "document_type_inference_enabled": true,
      "project_inference_skipped": false,
      "document_type_inference_skipped": false
    }
  }
}
```

### Project Inference Example

When no project IDs are specified, the system automatically detects project references:

**Request with Project Inference:**

``` json
{
  "query": "Coyote Hydrogen project zoning and land use information"
}
```

**Response with Automatic Project Filtering:**

``` json
{
  "vector_search": {
    "documents": [
      {
        "document_id": "uuid-string",
        "project_id": "proj-002",
        "project_name": "Coyote Hydrogen Project",
        "proponent_name": "Example Energy Corp",
        "content": "The zoning requirements for the facility include industrial designation and land use permits...",
        "relevance_score": -3.12,
        "search_quality": "normal"
      }
    ],
    "search_metrics": {...},
    "search_quality": "normal",
    "inference_settings": {
      "use_default_inference": true,
      "inference_parameter": null,
      "project_inference_enabled": true,
      "document_type_inference_enabled": true,
      "project_inference_skipped": false,
      "document_type_inference_skipped": false
    },
    "project_inference": {
      "attempted": true,
      "confidence": 0.88,
      "inferred_project_ids": ["proj-002"],
      "applied": true,
      "original_query": "Coyote Hydrogen project zoning and land use information",
      "cleaned_query": "zoning and land use information",
      "metadata": {
        "extracted_entities": ["Coyote Hydrogen project"],
        "matched_projects": [
          {
            "entity": "Coyote Hydrogen project",
            "project_id": "proj-002",
            "project_name": "Coyote Hydrogen Project",
            "similarity": 0.88
          }
        ],
        "reasoning": ["Detected entity 'Site C project' matching project 'Site C Clean Energy Project' with similarity 0.920"]
      }
    }
  }
}
```

### Inference with Explicit IDs Example

When explicit IDs are provided, inference is automatically skipped:

**Request with Explicit Project IDs:**

``` json
{
  "query": "environmental impact assessment",
  "project_ids": ["proj-123"],
  "inference": ["PROJECT", "DOCUMENTTYPE"]
}
```

**Response showing skipped inference:**

``` json
{
  "vector_search": {
    "documents": [...],
    "inference_settings": {
      "use_default_inference": true,
      "inference_parameter": ["PROJECT", "DOCUMENTTYPE"],
      "project_inference_enabled": true,
      "document_type_inference_enabled": true,
      "project_inference_skipped": true,
      "document_type_inference_skipped": false,
      "skip_reason": "explicit_ids_provided"
    }
  }
}
```

### Document Similarity Search

``` API
POST /api/document-similarity
```

Finds documents similar to a specified document using document-level embeddings.

**Request Body:**

``` json
{
  "document_id": "uuid-string",
  "project_ids": ["project-123"],  // Optional
  "limit": 10  // Optional, default: 10
}
```

### Processing Statistics

```http
GET /api/stats/processing
POST /api/stats/processing
```

Retrieves aggregated processing statistics across projects, including total files processed, success rates, and failure counts.

**GET Request:** Returns statistics for all projects.

**POST Request Body:**

```json
{
  "projectIds": ["project-123", "project-456"]
}
```

### Project Processing Details

```http
GET /api/stats/project/{project_id}
```

Provides detailed processing logs for a specific project including individual document processing records.

### Processing Summary

```http
GET /api/stats/summary
```

Provides a high-level summary of processing statistics across the entire system.

For detailed documentation on the Stats API, see [STATS_SERVICE.md](STATS_SERVICE.md).
