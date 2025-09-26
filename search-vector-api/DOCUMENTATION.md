# Search Vector API Documentation

## Overview

The Search Vector API provides advanced hybrid search capabilities using a modern multi-stage architecture that combines document-level keyword filtering with chunk-level semantic search. Built on PostgreSQL with pgvector extension, the system offers high-performance search with comprehensive fallback mechanisms and cross-encoder re-ranking.

## Architecture

### Hybrid Search Pipeline

The system implements an efficient hybrid search approach combining keyword and semantic search:

#### Stage 1: Document-Level Keyword Filtering

* Uses pre-computed document metadata (keywords, tags, headings) for fast document discovery
* Applies PostgreSQL full-text search on document-level metadata
* Applies project-based filtering constraints
* Identifies the most relevant documents before chunk-level search

#### Stage 2: Chunk-Level Semantic Search

* Performs semantic vector search within chunks of identified documents (from Stage 1)
* Uses pgvector for efficient similarity matching
* Maintains project filtering consistency

#### Search Fallback Strategy

* **Fallback 2.1**: Broader semantic search across all chunks if Stage 1 finds no documents
* **Fallback 2.2**: Keyword-based search on chunks as final fallback if semantic search fails
* Ensures relevant results when possible through multiple search strategies

#### Stage 3: Cross-Encoder Re-ranking

* Re-ranks results using advanced cross-encoder models for optimal relevance ordering
* Applies relevance score filtering to maintain quality standards

#### Direct Metadata Search Mode

* Activated when both project and document type are confidently inferred AND the query is generic
* Returns document-level results ordered by document date instead of semantic chunks
* Optimized for queries like "any correspondence for Project X" or "show me all letters for this project"
* Bypasses semantic search for faster, more relevant results when content analysis isn't needed

### Configurable Search Strategies

The API supports multiple search strategies that can be configured globally via environment variables or overridden per-request:

#### HYBRID_SEMANTIC_FALLBACK (Default)

The current default behavior implementing document-level filtering followed by semantic search:

1. **Document-Level Keyword Filtering**: Uses pre-computed document metadata (keywords, tags, headings) to identify relevant documents
2. **Chunk-Level Semantic Search**: Performs semantic vector search within chunks of identified documents
3. **Semantic Fallback**: If no documents found, searches all chunks semantically
4. **Keyword Fallback**: Final fallback to keyword search if semantic approaches fail

**Best for**: General-purpose queries, balanced efficiency and accuracy

#### HYBRID_KEYWORD_FALLBACK

Similar to the default but prioritizes keyword matching:

1. **Document-Level Keyword Filtering**: Same as default strategy
2. **Chunk-Level Keyword Search**: Performs keyword search within chunks of identified documents
3. **Keyword Fallback**: If no documents found, searches all chunks with keywords
4. **Semantic Fallback**: Final fallback to semantic search if keyword approaches fail

**Best for**: Queries with specific technical terms, exact phrase matching

#### SEMANTIC_ONLY

Pure semantic search without document-level filtering or keyword fallbacks:

1. **Direct Semantic Search**: Semantic vector search across all chunks
2. **Cross-Encoder Re-ranking**: Re-ranks all semantic results

**Best for**: Conceptual queries, when exact keyword matches aren't important

#### KEYWORD_ONLY

Pure keyword search without semantic components:

1. **Direct Keyword Search**: Keyword search across all chunks using PostgreSQL full-text search
2. **Cross-Encoder Re-ranking**: Re-ranks all keyword results

**Best for**: Exact term matching, fastest performance, queries with specific terminology

#### HYBRID_PARALLEL

Comprehensive search running both semantic and keyword approaches simultaneously with robust error handling:

1. **Parallel Execution**: Runs both semantic and keyword searches across all chunks in parallel threads with configurable timeouts
2. **Timeout Management**: Individual thread timeouts prevent indefinite hanging, with configurable timeout values
3. **Fallback Mechanism**: Falls back to sequential execution if parallel execution fails or times out
4. **Result Merging**: Combines results from both searches, removing duplicates based on chunk ID
5. **Cross-Encoder Re-ranking**: Re-ranks the merged result set for optimal relevance
6. **Enhanced Monitoring**: Detailed logging and metrics for thread completion, timeouts, and fallback usage

**Configuration Options**:

* `PARALLEL_SEARCH_TIMEOUT`: Maximum wait time for each search thread (default: 60 seconds)
* `PARALLEL_RESULT_COLLECTION_TIMEOUT`: Maximum wait time for collecting results from threads (default: 5 seconds)
* `ENABLE_PARALLEL_FALLBACK`: Enable fallback to sequential execution on parallel failure (default: true)

**Best for**: Maximum recall with robust handling of resource contention and timeout scenarios

#### Strategy Configuration

* **Environment Variable**: `DEFAULT_SEARCH_STRATEGY` sets the default strategy
* **Per-Request Override**: Use the `searchStrategy` parameter in API requests
* **Metrics Tracking**: All strategies include detailed timing metrics and strategy identification in responses

### Components

1. **Document-Level Keyword Search**: Fast filtering using pre-computed document metadata with PostgreSQL full-text search
2. **Chunk-Level Semantic Search**: Semantic search within document chunks using vector embeddings
3. **Keyword Fallback Search**: Final fallback using keyword search on chunks when semantic approaches fail
4. **Project Inference Service**: Intelligent project detection from natural language queries
5. **Vector Store**: Core service for vector and keyword operations with pgvector
6. **Embedding Service**: Text-to-vector conversion using sentence transformer models
7. **Keyword Extractor**: BERT-based keyword extraction from queries
8. **Tag Extractor**: Identifies tags in query text for filtering
9. **Re-Ranker**: Cross-encoder model for improved relevance scoring
10. **Search Orchestrator**: Manages the complete hybrid pipeline with multi-level fallback logic

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
   * `max_chunks_per_document`: Maximum number of chunks to return per document to prevent semantic bias
   * `top_record_count`: Number of top records to return after re-ranking
   * `reranker_batch_size`: Batch size for processing document re-ranking
   * `min_relevance_score`: Minimum relevance score for re-ranked results (default: -10.0)
   * `use_default_inference`: Whether to enable inference pipelines by default when not specified
   * `default_search_strategy`: Default search strategy when none specified in requests (default: HYBRID_SEMANTIC_FALLBACK)

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
    document_metadata JSONB,  -- Contains document-level metadata including document_date, project_name
    embedding VECTOR(768),    -- Document-level embedding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast document-level search
CREATE INDEX documents_keywords_idx ON documents USING GIN (document_keywords);
CREATE INDEX documents_tags_idx ON documents USING GIN (document_tags);  
CREATE INDEX documents_project_idx ON documents (project_id);
CREATE INDEX documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX documents_metadata_idx ON documents USING GIN (document_metadata);
CREATE INDEX documents_date_idx ON documents ((document_metadata->>'document_date'));
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
                    --   "document_metadata": {
                    --     "document_type": "string",
                    --     "document_name": "string",
                    --     "document_saved_name": "string",
                    --     "document_date": "YYYY-MM-DD"
                    --   },
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

The search process implements an intelligent multi-mode approach:

### Direct Metadata Search Process

When both project and document type are confidently inferred (e.g., from queries like "I am looking for any correspondence for the Coyote Hydrogen project"), the system:

1. **Detection**: Analyzes if the query is generic (requesting documents rather than specific content)
2. **Direct Query**: Queries the `documents` table directly by project_id and document_type_id
3. **Ordering**: Returns results ordered by document_date (newest first)
4. **Performance**: Extremely fast since no semantic analysis is required

**Direct Metadata Search Example:**

For generic document requests where both project and document type are inferred:

```json
{
  "query": "I am looking for any correspondence for the Coyote Hydrogen project"
}
```

**Response (Direct Metadata Mode):**

```json
{
  "vector_search": {
    "documents": [
      {
        "document_id": "uuid-string",
        "document_type": "Letter",
        "document_name": "response_letter.pdf",
        "document_saved_name": "Response to Public Comments 2023.pdf",
        "document_date": "2023-10-15",
        "page_number": null,
        "project_id": "project-coyote-hydrogen",
        "project_name": "Coyote Hydrogen Project",
        "proponent_name": "Coyote Energy Corp",
        "s3_key": "project-coyote/letters/response_letter.pdf",
        "content": "Full document available",
        "relevance_score": 1.0,
        "search_mode": "document_metadata"
      }
    ],
    "search_metrics": {
      "metadata_search_ms": 12.5,      // Direct metadata query time
      "formatting_ms": 2.1,            // Result formatting time
      "total_search_ms": 14.6,         // Total time (much faster)
      "search_mode": "direct_metadata"
    },
    "project_inference": {
      "attempted": true,
      "confidence": 0.92,
      "inferred_project_ids": ["project-coyote-hydrogen"],
      "applied": true,
      "metadata": {
        "extracted_entities": ["Coyote Hydrogen project"],
        "matched_projects": [...]
      }
    },
    "document_type_inference": {
      "attempted": true,
      "confidence": 0.85,
      "inferred_document_type_ids": ["5df79dd77b5abbf7da6f51be"],
      "applied": true,
      "metadata": {
        "extracted_entities": ["correspondence"],
        "matched_document_types": [...]
      }
    }
  }
}
```

### Two-Stage Semantic Search

For content-specific queries, the system implements an efficient two-stage approach:

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

## Inference Control

The search API supports fine-grained control over which inference pipelines run during query processing. This allows clients to:

* Enable/disable project inference
* Enable/disable document type inference  
* Use environment-based defaults
* Override defaults on a per-request basis

### Inference Configuration

#### Environment Variable

Add to your `.env` file:

```bash
# Set to true to enable default inference pipelines when inference parameter is not provided
# When false, no inference will run unless explicitly specified in the inference parameter
USE_DEFAULT_INFERENCE=true
```

**Default:** `true` (if not specified, all inference pipelines are enabled by default)

**Important:** If you don't include `USE_DEFAULT_INFERENCE` in your environment configuration, it automatically defaults to `true`, meaning both PROJECT and DOCUMENTTYPE inference will run when no `inference` parameter is provided in the API request.

### Request Parameter

The search request accepts an optional `inference` parameter:

```json
{
  "query": "water quality correspondence",
  "projectIds": [],  // optional
  "documentTypeIds": [],  // optional
  "inference": ["PROJECT", "DOCUMENTTYPE"]  // optional
}
```

#### Inference Parameter Values

| Value | Description |
|-------|-------------|
| `["PROJECT"]` | Only run project inference |
| `["DOCUMENTTYPE"]` | Only run document type inference |
| `["PROJECT", "DOCUMENTTYPE"]` | Run both inference pipelines |
| `[]` | Disable all inference pipelines |
| `null` or not provided | Use `USE_DEFAULT_INFERENCE` setting |

### Behavior Logic

The system determines which inference pipelines to run using this logic:

1. **If `inference` parameter is explicitly provided** (even if empty): Use it exactly as specified
2. **If `inference` parameter is `null`/not provided AND `USE_DEFAULT_INFERENCE=true` (or not set)**: Run all inference pipelines (PROJECT and DOCUMENTTYPE)
3. **If `inference` parameter is `null`/not provided AND `USE_DEFAULT_INFERENCE=false`**: Run no inference pipelines

**Key Point:** If you don't set `USE_DEFAULT_INFERENCE` in your environment at all, the system defaults to `true`, enabling all inference pipelines by default.

**Important:** Inference is automatically skipped when explicit IDs are provided, regardless of inference settings:

* If `projectIds` are provided in the request, PROJECT inference is skipped
* If `documentTypeIds` are provided in the request, DOCUMENTTYPE inference is skipped  
* This prevents unnecessary processing when IDs are already known

### Response Metadata

The search response includes inference settings in the metadata:

```json
{
  "vector_search": {
    "documents": [...],
    "search_metrics": {...},
    "inference_settings": {
      "use_default_inference": true,
      "inference_parameter": ["PROJECT", "DOCUMENTTYPE"],
      "project_inference_enabled": true,
      "document_type_inference_enabled": true,
      "project_inference_skipped": false,
      "document_type_inference_skipped": false,
      "skip_reason": null
    },
    "project_inference": {
      // ... project inference metadata if attempted
    },
    "document_type_inference": {
      // ... document type inference metadata if attempted
    }
  }
}
```

## Ranking Configuration

The search API supports fine-grained control over result filtering and ranking through the optional `ranking` object. This allows clients to:

* Configure minimum relevance score thresholds for filtering results
* Set maximum number of results to return after ranking
* Override environment defaults on a per-request basis
* Customize search precision vs recall behavior

### Ranking Environment Variables

Add to your `.env` file:

```bash
# Minimum relevance score threshold for filtering results
# Cross-encoder models can produce negative scores for relevant documents
MIN_RELEVANCE_SCORE=-8.0

# Maximum number of results to return after ranking
TOP_RECORD_COUNT=10
```

**Defaults:**

* `MIN_RELEVANCE_SCORE`: `-8.0` (more inclusive threshold)
* `TOP_RECORD_COUNT`: `10` (standard result count)

#### API Request Parameter

The search request accepts an optional `ranking` object:

```json
{
  "query": "environmental assessment reports",
  "projectIds": [],  // optional
  "documentTypeIds": [],  // optional
  "inference": ["PROJECT", "DOCUMENTTYPE"],  // optional
  "ranking": {  // optional
    "minScore": -6.0,
    "topN": 15
  }
}
```

#### Ranking Parameter Fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `minScore` | Float | No limit | Minimum relevance score threshold for filtering results |
| `topN` | Integer | 1-100 | Maximum number of results to return after ranking |

**Important Notes:**

* **Cross-encoder scores can be negative**: Relevant documents may have negative scores, so thresholds like `-6.0` or `-8.0` are normal
* **Lower minScore = more inclusive**: `-10.0` includes more results than `-5.0`
* **Higher minScore = more restrictive**: `-2.0` only includes highly relevant results
* **If not provided**: Uses environment variable defaults

### Ranking Behavior Logic

The system determines ranking parameters using this logic:

1. **If `ranking` object is provided**: Use specified `minScore` and/or `topN` values
2. **If `ranking.minScore` is null/not provided**: Use `MIN_RELEVANCE_SCORE` environment variable
3. **If `ranking.topN` is null/not provided**: Use `TOP_RECORD_COUNT` environment variable
4. **If `ranking` object is null/not provided**: Use both environment variable defaults

### Cross-Encoder Score Interpretation

The ranking system uses a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-2-v2`) that produces relevance scores:

* **Positive scores**: Generally indicate high relevance
* **Negative scores**: Can still indicate relevant documents - this is normal behavior
* **Score interpretation**: Relative ranking matters more than absolute values
* **Typical ranges**: Scores commonly range from `-15.0` to `+10.0`

### Ranking Examples

#### High Precision (Fewer, More Relevant Results)

```json
{
  "query": "environmental impact assessment",
  "ranking": {
    "minScore": -2.0,
    "topN": 5
  }
}
```

#### High Recall (More Results, Lower Threshold)

```json
{
  "query": "correspondence",
  "ranking": {
    "minScore": -10.0,
    "topN": 20
  }
}
```

#### Environment Defaults Only

```json
{
  "query": "project documents"
  // No ranking object - uses MIN_RELEVANCE_SCORE and TOP_RECORD_COUNT
}
```

### Ranking Response Metadata

The search response includes ranking information in the metrics:

```json
{
  "vector_search": {
    "document_chunks": [...],
    "search_metrics": {
      "ranking_config": {
        "minScore": {
          "value": -6.0,
          "source": "parameter"  // "parameter" if provided by user, "environment" if using defaults
        },
        "topN": {
          "value": 15,
          "source": "parameter"  // "parameter" if provided by user, "environment" if using defaults
        }
      },
      "filtering_total_chunks": 25,
      "filtering_excluded_chunks": 20,
      "filtering_exclusion_percentage": 80.0,
      "filtering_final_chunks": 5,
      "filtering_excluded_score_range": "-15.234 to -8.567",
      "filtering_included_score_range": "-5.123 to 2.456",
      "reranking_ms": 45.2
    }
  }
}
```

## Semantic Query Control

The search API supports optional user-provided semantic queries for advanced search optimization through the `semanticQuery` parameter. This feature allows advanced users to bypass automatic query cleaning and provide pre-optimized queries specifically for semantic/vector search operations.

### Semantic Query Overview

The `semanticQuery` parameter provides direct control over the query used for semantic search operations while preserving the original query for logging, display, and non-semantic operations.

### Semantic Query Use Cases

* **Query Optimization**: Provide a cleaned, focused query when you know the exact terms for semantic search
* **Bypassing Inference**: Skip automatic query processing when you have already optimized the query
* **Advanced Search Control**: Full control over semantic search while maintaining original query context
* **Testing and Debugging**: Compare results between original and optimized queries
* **Integration Workflows**: Allow external systems to provide pre-processed queries

### Semantic Query Parameter

The search request accepts an optional `semanticQuery` string:

```json
{
  "query": "find information about machine learning algorithms in the Coyote project",
  "semanticQuery": "machine learning algorithms",  // Optional: pre-optimized semantic query
  "projectIds": ["coyote-project-id"],
  "ranking": {
    "minScore": -6.0,
    "topN": 10
  }
}
```

### Semantic Query Behavior

The system determines which query to use for semantic operations using this priority:

1. **If `semanticQuery` is provided**: Use it directly for all semantic/vector search operations without modification
2. **If `semanticQuery` is not provided**: Apply automatic query cleaning and use inference results
3. **Always-applied cleaning**: Even with explicit project/document type IDs, semantic cleaning is applied unless `semanticQuery` is provided

### Semantic Query vs Original Query Usage

| Operation Type | Uses semanticQuery When Provided | Uses Original Query When semanticQuery Not Provided |
|---------------|-----------------------------------|---------------------------------------------------|
| Vector/Semantic Search | ✓ Direct usage, no cleaning | ✓ After automatic cleaning |
| Document-level Keyword Search | ✗ Always uses original query | ✓ Uses original query |
| Final Keyword Fallback | ✗ Always uses original query | ✓ Uses original query |
| Logging and Display | ✗ Always shows original query | ✓ Shows original query |
| Project Inference | ✗ Always uses original query | ✓ Uses original query |

### Response Indicators

The API response includes several fields to indicate semantic query processing:

```json
{
  "vector_search": {
    "document_chunks": [...],
    "search_metrics": {...},
    "original_query": "find information about machine learning algorithms",
    "final_semantic_query": "machine learning algorithms",
    "user_semantic_query_provided": true,
    "semantic_cleaning_applied": false,
    "additional_semantic_cleaning_applied": false,
    "query_processed": false
  }
}
```

### Response Field Descriptions

* **`original_query`**: The original query provided by the user
* **`final_semantic_query`**: The actual query used for semantic/vector search operations
* **`user_semantic_query_provided`**: Boolean indicating if user provided a `semanticQuery` parameter
* **`semantic_cleaning_applied`**: Boolean indicating if automatic semantic cleaning was applied
* **`additional_semantic_cleaning_applied`**: Boolean indicating if cleaning was applied for explicit ID cases
* **`query_processed`**: Boolean indicating if any query modification occurred

### Semantic Query Examples

#### Basic Usage

```json
{
  "query": "show me documents about renewable energy storage systems",
  "semanticQuery": "renewable energy storage"
}
```

#### With Project Filtering

```json
{
  "query": "find environmental assessments for the Wind Farm project",
  "semanticQuery": "environmental assessment",
  "projectIds": ["wind-farm-proj-001"]
}
```

#### Debugging Query Processing

```json
{
  "query": "look for information about machine learning algorithms"
  // No semanticQuery - compare automatic cleaning results
}
```

### API Endpoints

The Vector Search API provides several endpoint categories:

1. **Vector Search** (`/api/vector-search`) - Primary search functionality for documents
2. **Document Similarity** (`/api/document-similarity`) - Find similar documents
3. **Tools** (`/api/tools/*`) - Lightweight utilities for external systems and MCP tools
4. **Statistics** (`/api/stats/*`) - Processing metrics and project statistics
5. **Health** (`/healthz`, `/readyz`) - Service health and readiness checks

### Vector Search

```http
POST /api/vector-search
```

Performs the two-stage search pipeline with document-level filtering followed by chunk-level semantic search.

**Request Body:**

```json
{
  "query": "climate change impacts on wildlife",
  "semanticQuery": "climate change wildlife impact",    // Optional pre-optimized semantic query
  "projectIds": ["project-123", "project-456"],        // Optional project filtering
  "documentTypeIds": ["doc-type-123"],                 // Optional document type filtering
  "inference": ["PROJECT", "DOCUMENTTYPE"],            // Optional inference control
  "location": "Langford British Columbia",             // Optional location context
  "projectStatus": "recent",                           // Optional project status context
  "years": [2023, 2024, 2025],                        // Optional years context
  "ranking": {                                         // Optional ranking configuration
    "minScore": -6.0,
    "topN": 15
  }
}
```

**Response:**

```json
{
  "vector_search": {
    "document_chunks": [
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
        "relevance_score": -4.15,
        "search_mode": "semantic"
      }
    ],
    "search_metrics": {
      "ranking_config": {
        "minScore": {
          "value": -8.0,
          "source": "environment"
        },
        "topN": {
          "value": 10,
          "source": "environment"
        }
      },
      "document_search_ms": 1715.4,     // Stage 1: Document-level search time
      "chunk_search_ms": 126.49,       // Stage 2: Chunk-level search time within found documents
      "semantic_search_ms": 3787.95,   // Semantic search fallback time (when no documents found)
      "reranking_ms": 2659.92,         // Cross-encoder re-ranking time
      "formatting_ms": 0.0,            // Result formatting time
      "total_search_ms": 4502.32,      // Total search pipeline time
      "search_mode": "semantic"
    },
    "inference_settings": {
      "use_default_inference": true,
      "inference_parameter": ["PROJECT", "DOCUMENTTYPE"],
      "project_inference_enabled": true,
      "document_type_inference_enabled": true,
      "project_inference_skipped": false,
      "document_type_inference_skipped": false,
      "skip_reason": null
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

### Query Enhancement Parameters

The search API supports optional parameters that enhance search queries with additional context for improved semantic matching. These parameters are automatically integrated into the search query text to provide better contextual relevance.

#### Available Enhancement Parameters

**location** *(string, optional)*
* **Purpose**: Provides geographic context to improve location-specific searches
* **Usage**: Appended to the search query as "location: {value}"  
* **Examples**: 
  * `"Langford British Columbia"`
  * `"Northern BC"`
  * `"Vancouver Island"`
  * `"Lower Mainland"`

**projectStatus** *(string, optional)*
* **Purpose**: Adds project status context to filter by project phase or state
* **Usage**: Appended to the search query as "project status: {value}"
* **Examples**:
  * `"recent"` - Focus on recently active projects
  * `"active"` - Currently ongoing projects  
  * `"completed"` - Finished projects
  * `"proposed"` - Projects in planning phase

**years** *(array of integers, optional)*
* **Purpose**: Focuses search on specific years or timeframes
* **Usage**: Appended to the search query as "years: {comma-separated values}"
* **Examples**:
  * `[2023, 2024, 2025]` - Recent years
  * `[2020]` - Specific year
  * `[2018, 2019, 2020, 2021]` - Multi-year range

#### Query Enhancement Processing

When enhancement parameters are provided, they are automatically appended to the original query:

**Example Transformation:**
```
Original Query: "environmental impact assessment" 
Parameters: {
  "location": "Langford British Columbia",
  "projectStatus": "recent", 
  "years": [2023, 2024, 2025]
}
Enhanced Query: "environmental impact assessment (location: Langford British Columbia | project status: recent | years: 2023, 2024, 2025)"
```

The enhanced query is then processed through the normal search pipeline, allowing the semantic and keyword search components to utilize the additional context for improved relevance matching.

#### Future Enhancements

These parameters are currently integrated as text enhancements. Future versions may implement:
* Direct database filtering on temporal fields
* Geographic metadata filtering  
* Project status-based result ranking
* Advanced temporal query processing

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

### Document Type Handling

The search system ensures that all API responses include a `document_type` field with human-readable document type names. The system supports multiple data sources for document type information:

#### Chunk-Level Results (Primary)

For search results based on document chunks, the system prioritizes document type information stored in the chunk metadata:

1. **Nested Document Metadata** (Preferred): `chunk_metadata.document_metadata.document_type`
   * This is the standard approach where chunk metadata contains a `document_metadata` object
   * The `document_type` field within this object contains the human-readable type name

2. **Direct Field** (Legacy Support): `chunk_metadata.document_type`
   * For backward compatibility with older chunk metadata structures
   * Used as fallback when nested structure is not available

#### Document-Level Results (Fallback)

For document-level search results, the system uses document metadata:

1. **Direct Document Type**: `document_metadata.documentType`
   * Human-readable document type name stored directly in document metadata

2. **Document Type ID Lookup**: `document_metadata.documentTypeId`
   * Numeric ID that gets mapped to human-readable names using the document type lookup table
   * Used when direct type name is not available

#### Metadata Structure Examples

**Preferred Chunk Metadata Structure:**

```json
{
  "document_id": "uuid-string",
  "document_metadata": {
    "document_type": "Environmental Assessment",
    "document_name": "Climate_Impact_Study.pdf",
    "document_saved_name": "Climate Impact Assessment 2023.pdf"
  },
  "page_number": "15",
  "project_id": "project-123",
  "project_name": "Climate Research Initiative"
}
```

**Legacy Chunk Metadata Structure:**

```json
{
  "document_id": "uuid-string",
  "document_type": "Environmental Assessment",
  "document_name": "Climate_Impact_Study.pdf",
  "page_number": "15",
  "project_id": "project-123"
}
```

This hierarchical approach ensures robust document type population while supporting different metadata structures that may exist in the system.

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
| MAX_CHUNKS_PER_DOCUMENT | Maximum number of chunks to return per document to prevent semantic bias | 10 |
| TOP_RECORD_COUNT | Number of top records to return after re-ranking | 10 |
| RERANKER_BATCH_SIZE | Batch size for the cross-encoder re-ranker | 8 |
| MIN_RELEVANCE_SCORE | Minimum relevance score for re-ranked results | 0.0 |
| USE_DEFAULT_INFERENCE | Enable all inference pipelines by default when inference parameter is not provided | true |

#### ML Model Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| CROSS_ENCODER_MODEL | Model for re-ranking results | cross-encoder/ms-marco-MiniLM-L-2-v2 |
| EMBEDDING_MODEL_NAME | Model for generating embeddings | all-mpnet-base-v2 |
| KEYWORD_MODEL_NAME | Model for keyword extraction | all-mpnet-base-v2 |
| DOCUMENT_KEYWORD_EXTRACTION_METHOD | Method used for document keyword extraction | keybert |

#### Keyword Extraction Configuration

The system supports two different keyword extraction methods, which affects the query engine's search strategy:

| Method | Description | Query Strategy | Best For |
|--------|-------------|---------------|----------|
| `keybert` (default) | Semantic embeddings-based extraction using KeyBERT | Match query keywords directly with document keywords | High semantic relevance, standard/fast embedding modes |
| `tfidf` | Statistical frequency-based extraction using TF-IDF | Prioritize tags/headings over keywords, rely more on semantic search | Simplified mode, statistical frequency matching |

**Configuration:**

```bash
# Set the keyword extraction method to match your document processing pipeline
DOCUMENT_KEYWORD_EXTRACTION_METHOD=keybert  # or "tfidf"
```

**Impact on Search Behavior:**

1. **KeyBERT Mode** (default):
   * Query keywords extracted using KeyBERT with semantic embeddings
   * Document-level search prioritizes keyword matching since both use semantic extraction
   * High-quality semantic relevance between query and document keywords
   * Works with diversity settings (0.6-0.7) from standard and fast modes

2. **TF-IDF Mode**:
   * Query keywords extracted using TF-IDF statistical methods
   * Document-level search prioritizes tags and headings over keyword matching
   * Search strategy relies more heavily on semantic vector search for accuracy
   * Optimized for documents processed with simplified/fast TF-IDF extraction

**Example Configuration for TF-IDF:**

```bash
# When your embedding service uses TF-IDF for document keywords
DOCUMENT_KEYWORD_EXTRACTION_METHOD=tfidf
```

The search metrics will include the extraction method used:

```json
{
  "search_metrics": {
    "keyword_extraction_method": "tfidf",
    "document_search_ms": 45.2,
    // ... other metrics
  }
}
```

**Migration Note**: To switch from KeyBERT to TF-IDF mode, simply update your `.env` file with the new configuration and restart the application. The system is fully backward compatible and defaults to KeyBERT mode if not configured.
    "document_search_ms": 45.2,
    // ... other metrics
  }
}

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

### Tools API

The Tools API provides lightweight utility endpoints for external tools and MCP (Model Context Protocol) systems. It offers simplified access to project listings and document type information without the overhead of processing statistics.

#### Projects List
The API provides two distinct success rate metrics:

* **Overall Success Rate**: Includes all files (successful / total_files) - provides insight into file selection and processing pipeline
* **Processing Success Rate**: Excludes skipped files (successful / processed_files) - focuses on actual processing pipeline effectiveness


```http
GET /api/tools/projects
```

Retrieves a simple list of all projects with basic information (ID and name only).

**Response:**

```json
{
  "projects": [
    {
      "project_id": "project-123",
      "project_name": "Site C Clean Energy Project"
    },
    {
      "project_id": "project-456", 
      "project_name": "Trans Mountain Pipeline"
    }
  ],
  "total_projects": 2
}
```

#### Document Types List

```http
GET /api/tools/document-types
```

Retrieves comprehensive document type information including names, IDs, and aliases for both 2002 Act and 2018 Act terms.

**Response:**

```json
{
  "document_types": {
    "5cf00c03a266b7e1877504ca": {
      "name": "Request",
      "aliases": ["request", "requests", "inquiry", "inquiries"],
      "act": "2002_act_terms"
    },
    "5cf00c03a266b7e1877504cb": {
      "name": "Letter",
      "aliases": ["letter", "letters", "correspondence", "email", "emails"],
      "act": "2002_act_terms"
    }
  },
  "lookup_only": {
    "5cf00c03a266b7e1877504ca": "Request",
    "5cf00c03a266b7e1877504cb": "Letter"
  },
  "total_types": 42,
  "act_breakdown": {
    "2002_act_terms": 20,
    "2018_act_terms": 22
  }
}
```

#### Document Type Details

```http
GET /api/tools/document-types/{type_id}
```

Retrieves detailed information for a specific document type by ID.

**Response:**

```json
{
  "document_type": {
    "id": "5cf00c03a266b7e1877504ca",
    "name": "Request", 
    "aliases": ["request", "requests", "inquiry", "inquiries"],
    "act": "2002_act_terms"
  }
}
```

**Error Response (404):**

```json
{
  "document_type": null,
  "error": "Document type ID 'invalid-id' not found"
}
```

#### Search Strategies

```http
GET /api/tools/search-strategies
```

Retrieves all available search strategies supported by the API, including semantic, keyword, hybrid, and metadata search options with their descriptions and capabilities.

**Response:**

```json
{
  "search_strategies": [
    {
      "name": "semantic",
      "description": "AI-powered semantic search using embeddings",
      "capabilities": ["natural_language", "contextual_understanding", "similarity_matching"],
      "parameters": ["embedding_model", "similarity_threshold"]
    },
    {
      "name": "keyword", 
      "description": "Traditional keyword-based search",
      "capabilities": ["exact_match", "boolean_operators", "phrase_matching"],
      "parameters": ["query_string", "case_sensitive"]
    },
    {
      "name": "hybrid",
      "description": "Combined semantic and keyword search with ranking",
      "capabilities": ["best_of_both", "weighted_results", "precision_recall_balance"],
      "parameters": ["semantic_weight", "keyword_weight", "ranking_algorithm"]
    },
    {
      "name": "metadata",
      "description": "Search based on document metadata fields",
      "capabilities": ["structured_search", "faceted_filtering", "date_ranges"],
      "parameters": ["metadata_fields", "filter_criteria", "date_range"]
    }
  ]
}
```

#### Inference Options

```http
GET /api/tools/inference-options
```

Retrieves all available inference options for document classification, including document type classification and project inference services.

**Response:**

```json
{
  "inference_options": [
    {
      "service": "document_type_inference",
      "description": "Automatic document type classification using ML models",
      "input_format": "text_content",
      "output_format": {
        "document_type": "string",
        "confidence_score": "float",
        "alternatives": "array"
      },
      "capabilities": ["multi_class_classification", "confidence_scoring", "alternative_suggestions"]
    },
    {
      "service": "project_inference", 
      "description": "Automatic project classification and assignment",
      "input_format": "document_metadata",
      "output_format": {
        "project_id": "string",
        "project_name": "string", 
        "confidence_score": "float"
      },
      "capabilities": ["project_matching", "metadata_analysis", "confidence_scoring"]
    }
  ]
}
```

#### API Capabilities

```http
GET /api/tools/api-capabilities
```

Retrieves comprehensive information about API capabilities, endpoints, methods, and parameters. Useful for MCP tools and external integrations to discover API functionality.

**Response:**

```json
{
  "api_capabilities": {
    "version": "1.0",
    "base_url": "/api",
    "endpoints": {
      "search": {
        "path": "/vector-search",
        "methods": ["POST"],
        "capabilities": ["semantic_search", "keyword_search", "hybrid_search", "metadata_filtering"],
        "parameters": {
          "required": ["query"],
          "optional": ["project_ids", "document_types", "limit", "offset", "search_strategy"]
        }
      },
      "similarity": {
        "path": "/document-similarity",
        "methods": ["POST"],
        "capabilities": ["similarity_search", "document_matching", "content_recommendation"],
        "parameters": {
          "required": ["document_id"],
          "optional": ["project_ids", "limit"]
        }
      },
      "tools": {
        "path": "/tools",
        "methods": ["GET"],
        "capabilities": ["project_listing", "document_type_lookup", "api_discovery"],
        "endpoints": [
          "/tools/projects",
          "/tools/document-types", 
          "/tools/document-types/{type_id}",
          "/tools/search-strategies",
          "/tools/inference-options",
          "/tools/api-capabilities"
        ]
      },
      "stats": {
        "path": "/stats", 
        "methods": ["GET"],
        "capabilities": ["processing_statistics", "project_metrics", "failure_analysis"],
        "endpoints": [
          "/stats/processing",
          "/stats/processing/{project_id}",
          "/stats/summary"
        ]
      },
      "health": {
        "path": "/",
        "methods": ["GET"],
        "capabilities": ["health_monitoring", "readiness_check", "service_status"],
        "endpoints": [
          "/healthz",
          "/readyz"
        ]
      }
    },
    "data_formats": {
      "input": ["application/json", "text/plain"],
      "output": ["application/json"]
    },
    "authentication": {
      "required": false,
      "methods": []
    }
  }
}
```

### Statistics API

The Stats API provides comprehensive processing statistics and metrics for document processing operations. It tracks document processing success rates, failure counts, skipped counts, and detailed logs by joining data from the `processing_logs` and `projects` tables.

#### Processing Statistics

```http
GET /api/stats/processing
```

Retrieves aggregated processing statistics across all projects.

**Request:**

```http
GET /api/stats/processing
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
        "failed_files": 8,
        "skipped_files": 2,
        "overall_success_rate": 93.33,
        "processing_success_rate": 94.59
      }
    ],
    "summary": {
      "total_projects": 5,
      "total_files_across_all_projects": 750,
      "total_successful_files": 720,
      "total_failed_files": 25,
      "total_skipped_files": 5,
      "overall_success_rate": 96.0,
      "overall_processing_success_rate": 96.64
    }
  }
}
```

#### Project Processing Details

```http
GET /api/stats/processing/{project_id}
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
      "successful_files": 46,
      "failed_files": 2,
      "skipped_files": 2,
      "overall_success_rate": 92.0,
      "processing_success_rate": 95.83
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
    "overall_processing_success_rate": 96.0,
    "projects_with_failures": 2,
    "projects_with_skipped_files": 1,
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
* `status` (VARCHAR: "success", "failure", or "skipped")
* `processed_at` (TIMESTAMP)
* `metrics` (JSONB)

## Future Enhancements

* Add authentication and rate limiting
* Implement caching for frequent queries
* Support for more advanced filtering options
* Vector quantization for larger datasets
* Personalized search results based on user preferences
* Support for more language models and embedding techniques

### Response Structure

The API returns different response structures based on the search mode:

#### Document-Level Results (`documents`)

**When**: Direct Metadata Search Mode (generic queries like "any correspondence for Project X")
**Structure**: Document-level results ordered by date
**Key**: `"documents"`
**Features**:

* `page_number`: Always `null` (document-level results)
* `content`: "Full document available"
* `search_mode`: "document_metadata"
* `relevance_score`: 1.0 (perfect metadata match)

#### Chunk-Level Results (`document_chunks`)

**When**: Semantic Search Mode (content-specific queries)
**Structure**: Document chunk results ranked by semantic relevance
**Key**: `"document_chunks"`
**Features**:

* `page_number`: Actual page number where chunk was found
* `content`: Relevant chunk text content  
* `search_mode`: "semantic"
* `relevance_score`: Cross-encoder relevance score

This distinction makes it clear whether you're getting complete documents or specific content chunks, improving API usability and client-side processing.

### Search Metrics

The API returns detailed timing metrics for each stage of the search pipeline:

#### Ranking Configuration Metrics

* **`ranking_config`**: Shows the ranking parameters used for the search
  * `minScore.value`: The minimum relevance score threshold applied
  * `minScore.source`: Whether the value came from user parameter or environment default
  * `topN.value`: The maximum number of results returned
  * `topN.source`: Whether the value came from user parameter or environment default

#### Timing Metrics

* **`document_search_ms`**: Time spent searching the documents table using keywords, tags, and headings (Stage 1)
* **`chunk_search_ms`**: Time spent searching chunks within identified documents (Stage 2 - normal path)  
* **`semantic_search_ms`**: Time spent on semantic search across all chunks when no documents found (alternative search path)
* **`metadata_search_ms`**: Time spent on direct metadata search for generic queries (Direct Metadata Search Mode)
* **`reranking_ms`**: Time spent re-ranking results using the cross-encoder model
* **`formatting_ms`**: Time spent formatting final results
* **`total_search_ms`**: Total time for the complete search pipeline

#### Search Mode Indicators

* **`search_mode`**: Indicates which search strategy was used:
  * `"semantic"`: Two-stage semantic search with possible fallback
  * `"direct_metadata"`: Direct metadata search for generic queries

**Note**: Only relevant timing metrics are included in each response. For example, `chunk_search_ms` and `semantic_search_ms` are mutually exclusive - you'll see one or the other, but not both in the same response.
