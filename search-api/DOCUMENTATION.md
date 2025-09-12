# SEARCH-API Documentation

## Overview

The Search-API is a Flask-based REST API service that implements a Retrieval-Augmented Generation (RAG) pattern. It provides a bridge between user queries, an external vector search service, and an LLM (Language Learning Model) to generate contextually relevant responses.

## Architecture

The service follows a modular architecture with the following key components:

1. **REST API Layer**: Handles incoming HTTP requests and responses
2. **Search Service**: Coordinates the search flow between vector search and LLM synthesis
3. **Agentic Service**: Orchestrates AI-powered query analysis and optimization using direct LLM calls
4. **LLM Integration**: Provides intelligent query processing using LLMs for parameter extraction and validation
5. **Generation Services**: Manages LLM integration for response generation and agentic processing
6. **External Vector Search**: Retrieves relevant document information based on processed queries

### Environment-Aware Architecture

The system automatically adapts based on deployment environment:

#### Local Development Architecture

- **LLM Mode**: Direct client integration
- **LLM Provider**: Ollama (local models) or OpenAI
- **Use Case**: Development, debugging, experimentation

#### Production/Azure Architecture

- **LLM Mode**: Direct client integration
- **LLM Provider**: Azure OpenAI
- **Use Case**: Scalable cloud deployment

The Search API provides intelligent parameter extraction and query validation through a modular generation services architecture with support for multiple LLM providers.

**Key Generation Services:**

- **Parameter Extractor**: Multi-step extraction for project IDs, document types, and search strategy
- **Query Validator**: LLM-powered validation for query relevance and scope
- **Summarizer**: Response synthesis and document summarization

For deployment configuration across different environments, see the **[Deployment Guide](#deployment-guide)** section below.

## Component Diagram

The service architecture supports environment-aware deployment with intelligent agentic processing:

### Local Development Architecture (Ollama/OpenAI + Direct LLM Integration)

```mermaid
flowchart TD
    Client["Client Application"] --> SearchAPI["Search API (Flask)"]
    SearchAPI --> AgenticService["Agentic Service"]
    AgenticService --> ParameterExtractor["Parameter Extractor"]
    AgenticService --> QueryValidator["Query Validator"]
    ParameterExtractor --> LLMClient["LLM Client (Ollama/OpenAI)"]
    QueryValidator --> LLMClient
    AgenticService --> VectorSearch["Vector Search Service"]
    SearchAPI --> Summarizer["LLM Summarizer"]
    Summarizer --> LLMClient
    VectorSearch --> ExternalVector["External Vector API"]
    
    style LLMClient fill:#e1f5fe
    style ParameterExtractor fill:#e8f5e8
    style QueryValidator fill:#fff3e0
```

### Production/Azure Architecture (Azure OpenAI + Direct LLM Integration)

```mermaid
flowchart TD
    Client["Client Application"] --> SearchAPI["Search API (Flask)"]
    SearchAPI --> AgenticService["Agentic Service"] 
    AgenticService --> ParameterExtractor["Parameter Extractor"]
    AgenticService --> QueryValidator["Query Validator"]
    ParameterExtractor --> AzureOpenAI["Azure OpenAI"]
    QueryValidator --> AzureOpenAI
    AgenticService --> VectorSearch["Vector Search Service"]
    SearchAPI --> Summarizer["LLM Summarizer"]
    Summarizer --> AzureOpenAI
    VectorSearch --> ExternalVector["External Vector API"]
    AzureOpenAI -.-> PrivateEndpoint["Private Endpoint"]
    
    style AzureOpenAI fill:#fff3e0
    style ParameterExtractor fill:#e8f5e8
    style QueryValidator fill:#e3f2fd
```

### Agentic Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as Search API
    participant Agentic as Agentic Service
    participant Validator as Query Validator
    participant Extractor as Parameter Extractor
    participant LLM as LLM (Ollama/OpenAI)
    participant Vector as Vector Search
    
    Client->>API: POST /api/search/query (agentic=true)
    API->>Agentic: Process with intelligence
    
    Note over Agentic,LLM: Query Relevance Check
    Agentic->>Validator: validate_query_relevance
    Validator->>LLM: Analyze query scope
    LLM->>Validator: EAO relevance score
    Validator->>Agentic: Relevance result
    
    Note over Agentic,LLM: Multi-Step Parameter Extraction
    Agentic->>Extractor: extract_parameters
    Extractor->>LLM: Step 1: Extract project IDs
    LLM->>Extractor: Project ID suggestions
    Extractor->>LLM: Step 2: Extract document types
    LLM->>Extractor: Document type IDs
    Extractor->>LLM: Step 3: Extract strategy & query
    LLM->>Extractor: Search strategy & semantic query
    Extractor->>Agentic: Complete parameters
    
    Agentic->>Vector: Execute search with extracted parameters
    Vector->>API: Search results
    API->>LLM: Generate response summary
    LLM->>API: Final response
    API->>Client: Results + agentic insights
```

## Workflow

The Search API supports both traditional and agentic workflow modes:

### Traditional Workflow

1. Client sends a search query through REST API
2. Search Service forwards the query directly to the external Vector Search service
3. Vector Search service returns relevant document information
4. Search Service formats the documents and creates a prompt for the LLM
5. Based on configuration:
   - **Local Development**: Ollama processes the prompt for response synthesis
   - **Azure Production**: Azure OpenAI processes the prompt through private endpoint
6. Search Service formats the response and returns it to the client with document information and performance metrics

### Agentic Workflow (agentic=true)

1. Client sends a search query with agentic flag through REST API
2. **Query Relevance Validation**: LLM-powered validation service validates if query is EAO-related
   - **Local**: Ollama analyzes query scope and relevance
   - **Azure**: Azure OpenAI analyzes query scope and relevance
   - If non-EAO query detected, returns helpful scope guidance
3. **Multi-Step Parameter Extraction**: LLM extraction service intelligently extracts search parameters
   - **Step 1**: LLM extracts project IDs using fuzzy matching
   - **Step 2**: LLM extracts document types via comprehensive alias search
   - **Step 3**: LLM determines optimal search strategy and creates semantic query
   - Caches project/document type mappings for efficient processing
4. **Search Strategy Optimization**: LLM service recommends optimal search approach
   - **Local**: Ollama analyzes query characteristics for strategy selection
   - **Azure**: Azure OpenAI analyzes query characteristics for strategy selection
5. Search Service executes optimized search with extracted parameters on Vector Search service
6. Vector Search service returns targeted, relevant document information
7. **Response Synthesis**: LLM generates final response summary
   - **Local**: Ollama synthesizes response from search results
   - **Azure**: Azure OpenAI synthesizes response through private endpoint
8. Search Service returns enhanced results with:
   - Original search results
   - Agentic insights (relevance, extracted parameters, strategy recommendations)
   - Confidence scores and reasoning
   - Performance metrics for both LLM processing and search execution

### Environment-Aware LLM Integration

- **Local Development**: All LLM calls (agentic + synthesis) use Ollama for consistent local experience
- **Azure Production**: All LLM calls (agentic + synthesis) use Azure OpenAI for enterprise-grade performance
- **Automatic Detection**: Environment detection ensures appropriate LLM provider without manual configuration

## API Endpoints

### GET /api/document/view

Retrieves and displays a PDF document stored in S3.

**Query Parameters:**

- `key` - (Required) The S3 key of the document, URL encoded
- `file_name` - (Required) The filename to display in the browser, URL encoded

**Example Request:**

```code
GET /api/document/view?key=path%2Fto%2Fdocument.pdf&file_name=document.pdf
```

**Authentication:**

- Currently disabled for development, but will require standard authentication headers when re-enabled
- The @auth.require decorator will be used to enforce authentication

**Response:**

- Content-Type: application/pdf
- Content-Disposition: inline; filename="document.pdf"
- Body: Binary PDF data
- Cache-Control headers for optimal browser caching

**Error Responses:**

- 400 Bad Request - Missing required parameters
- 404 Not Found - Document not found or inaccessible
- 500 Internal Server Error - Server error

### POST /api/search/query

Processes a search query and returns relevant documents with an LLM-generated summary.

**Request:**

```json
{
  "query": "What is the environmental impact of the project?",
  "projectIds": ["P-123"],
  "documentTypeIds": ["doc-type-1", "doc-type-2"],
  "inference": ["PROJECT", "DOCUMENTTYPE"],
  "ranking": {
    "minScore": 0.7,
    "topN": 10
  },
  "searchStrategy": "HYBRID_PARALLEL"
}
```

**Request Parameters:**

- `query` (string, required): The search query
- `projectIds` (array, optional): List of project IDs to filter search results by. If not provided, searches across all projects
- `documentTypeIds` (array, optional): List of document type IDs to filter search results by. If not provided, searches across all document types
- `inference` (array, optional): List of inference types to enable (e.g., ["PROJECT", "DOCUMENTTYPE"]). If not provided, uses the vector search API's default inference settings
- `ranking` (object, optional): Ranking configuration with keys like 'minScore' and 'topN'. If not provided, uses the vector search API's default ranking settings
- `searchStrategy` (string, optional): Search strategy to use. Available options:
  - `HYBRID_SEMANTIC_FALLBACK` (default): Document-level filtering → semantic search → semantic fallback → keyword fallback. Best for general-purpose queries with balanced efficiency and accuracy
  - `HYBRID_KEYWORD_FALLBACK`: Document-level filtering → keyword search → keyword fallback → semantic fallback. Best for queries with specific technical terms and exact phrase matching
  - `SEMANTIC_ONLY`: Pure semantic search without document-level filtering or keyword fallbacks. Best for conceptual queries when exact keyword matches aren't important
  - `KEYWORD_ONLY`: Pure keyword search without semantic components. Best for exact term matching and fastest performance
  - `HYBRID_PARALLEL`: Runs both semantic and keyword searches simultaneously then merges results. Best for maximum recall when computational cost is not a concern

**Response:**

```json
{
  "result": {
    "response": "LLM-generated summary based on the documents",
    "documents": [
      {
        "document_id": "123",
        "document_name": "Environmental Assessment Report",
        "document_type": "Report",
        "content": "Document content excerpt...",
        "page_number": "45",
        "project_id": "P-123",
        "project_name": "Example Project"
      }
    ],
    "metrics": {
      "start_time": "2025-07-17 14:30:45 UTC",
      "get_synthesizer_time": 12.34,
      "llm_provider": "openai",
      "llm_model": "gpt-41-nano",
      "search_time_ms": 234.56,
      "search_breakdown": {
        "search_strategy": "HYBRID_PARALLEL",
        "search_query": "environmental impact",
        "project_filter_applied": true,
        "document_type_filter_applied": false,
        "document_search_ms": 45.2,
        "semantic_search_ms": 123.4,
        "keyword_search_ms": 89.1,
        "reranking_ms": 67.8,
        "total_search_ms": 325.5
      },
      "llm_time_ms": 345.67,
      "total_time_ms": 592.57,
      "search_quality": "normal",
      "original_query": "What is the environmental impact of the project?",
      "final_semantic_query": "environmental impact project",
      "semantic_cleaning_applied": true,
      "search_mode": "hybrid_parallel",
      "query_processed": true,
      "inference_settings": {
        "use_default_inference": true,
        "project_inference_enabled": true,
        "document_type_inference_enabled": true
      }
    },
    "search_quality": "normal",
    "project_inference": {
      "attempted": true,
      "confidence": 0.95,
      "inferred_project_ids": ["P-123"],
      "applied": true
    },
    "document_type_inference": {
      "attempted": true,
      "confidence": 0.85,
      "inferred_document_type_ids": ["doc-type-1"],
      "applied": true
    }
  }
}
```

### POST /api/search/document-similarity

Finds documents similar to a given document using document-level embeddings.

**Request:**

```json
{
  "documentId": "65130ee0381111002240b89e",
  "projectIds": ["P-123"],
  "limit": 5
}
```

**Response:**

```json
{
  "result": {
    "source_document_id": "65130ee0381111002240b89e",
    "documents": [
      {
        "document_id": "651c37412c14e00022713dad",
        "document_keywords": ["shared lheidli", "environmental assessment"],
        "document_tags": ["Employment", "Communities"],
        "document_headings": [],
        "project_id": "650b5adc5d77c20022fb59fc",
        "similarity_score": 0.8553,
        "created_at": "2025-07-07T20:24:32.738719+00:00"
      }
      // ... more similar documents ...
    ],
    "metrics": {
      "start_time": "2025-07-10 12:00:00 UTC",
      "search_time_ms": 114.24,
      "search_breakdown": { /* detailed timing */ },
      "total_time_ms": 120.00
    }
  }
}
```

### GET /api/stats/processing

Returns processing statistics for all projects.

**Response:**

```json
{
  "result": {
    "processing_stats": { /* stats data */ },
    "metrics": { /* timing and meta info */ }
  }
}
```

### GET /api/stats/processing/<project_id>

Returns detailed processing logs for a specific project.

**Response:**

```json
{
  "result": {
    "project_details": { /* project log data */ },
    "metrics": { /* timing and meta info */ }
  }
}
```

### GET /api/stats/summary

Returns a high-level processing summary across the entire system.

**Response:**

```json
{
  "result": {
    "system_summary": { /* summary data */ },
    "metrics": { /* timing and meta info */ }
  }
}
```

## Search Strategies

The API supports multiple configurable search strategies that can be specified using the `searchStrategy` parameter in search requests. Each strategy optimizes for different use cases and performance characteristics.

### HYBRID_SEMANTIC_FALLBACK (Default)

**Description**: The balanced approach implementing document-level filtering followed by semantic search with fallback mechanisms.

**Flow**:

1. **Document-Level Keyword Filtering**: Uses pre-computed document metadata (keywords, tags, headings) to identify relevant documents
2. **Chunk-Level Semantic Search**: Performs semantic vector search within chunks of identified documents
3. **Semantic Fallback**: If no documents found, searches all chunks semantically
4. **Keyword Fallback**: Final fallback to keyword search if semantic approaches fail

**Best For**: General-purpose queries, balanced efficiency and accuracy

**Usage**:

```json
{
  "query": "What are the environmental impacts?",
  "searchStrategy": "HYBRID_SEMANTIC_FALLBACK"
}
```

### HYBRID_KEYWORD_FALLBACK

**Description**: Similar to the default but prioritizes keyword matching over semantic search.

**Flow**:

1. **Document-Level Keyword Filtering**: Same as default strategy
2. **Chunk-Level Keyword Search**: Performs keyword search within chunks of identified documents
3. **Keyword Fallback**: If no documents found, searches all chunks with keywords
4. **Semantic Fallback**: Final fallback to semantic search if keyword approaches fail

**Best For**: Queries with specific technical terms, exact phrase matching

**Usage**:

```json
{
  "query": "carbon dioxide emissions monitoring",
  "searchStrategy": "HYBRID_KEYWORD_FALLBACK"
}
```

### SEMANTIC_ONLY

**Description**: Pure semantic search without document-level filtering or keyword fallbacks.

**Flow**:

1. **Direct Semantic Search**: Semantic vector search across all chunks
2. **Cross-Encoder Re-ranking**: Re-ranks all semantic results

**Best For**: Conceptual queries, when exact keyword matches aren't important

**Usage**:

```json
{
  "query": "What are the community concerns?",
  "searchStrategy": "SEMANTIC_ONLY"
}
```

### KEYWORD_ONLY

**Description**: Pure keyword search without semantic components.

**Flow**:

1. **Direct Keyword Search**: Keyword search across all chunks using PostgreSQL full-text search
2. **Cross-Encoder Re-ranking**: Re-ranks all keyword results

**Best For**: Exact term matching, fastest performance, queries with specific terminology

**Usage**:

```json
{
  "query": "section 11 environmental assessment",
  "searchStrategy": "KEYWORD_ONLY"
}
```

### HYBRID_PARALLEL

**Description**: Comprehensive search running both semantic and keyword approaches simultaneously.

**Flow**:

1. **Parallel Execution**: Runs both semantic and keyword searches across all chunks in parallel threads
2. **Result Merging**: Combines results from both searches, removing duplicates
3. **Cross-Encoder Re-ranking**: Re-ranks the merged result set

**Best For**: Maximum recall, when computational cost is not a concern

**Usage**:

```json
{
  "query": "wildlife habitat protection measures",
  "searchStrategy": "HYBRID_PARALLEL"
}
```

### Strategy Selection Guidelines

- **Use HYBRID_SEMANTIC_FALLBACK** for most general queries where you want balanced performance and accuracy
- **Use HYBRID_KEYWORD_FALLBACK** when searching for specific technical terms, regulatory references, or exact phrases
- **Use SEMANTIC_ONLY** for conceptual or thematic queries where understanding context is more important than exact matches
- **Use KEYWORD_ONLY** for fastest performance when you need exact term matching
- **Use HYBRID_PARALLEL** when you need maximum recall and computational resources allow for parallel processing

### Metrics and Monitoring

All search strategies include detailed timing metrics in the response:

- Strategy identification and source (default vs. request-specified)
- Per-component timing (document filtering, semantic search, keyword search, re-ranking)
- Filtering statistics (total chunks, excluded chunks, score ranges)
- Inference timing and breakdown

## Complete API Coverage

The Search API implements a comprehensive set of endpoints supporting both UI-driven and agentic workflows. This section provides complete coverage of all available endpoints.

### Coverage Statistics

🎉 **COMPLETE PARITY ACHIEVED!**

- **Total Coverage**: 13/13 Vector API endpoints (100%)
- **Search Operations**: 2/2 (100%)  
- **Discovery Operations**: 6/6 (100%)
- **Statistics Operations**: 3/3 (100%)
- **Health Operations**: 2/2 (100%)

### 🔍 Search Endpoints

See detailed documentation above for comprehensive endpoint information:

- **POST /api/search/query** - Primary search endpoint with LLM synthesis. Supports inference, ranking, and multiple search strategies
- **POST /api/search/document-similarity** - Document-level similarity search using document embeddings. Replaces the deprecated `/similar` endpoint

### 📋 Discovery Endpoints (Tools)

#### GET /api/tools/projects

Returns lightweight list of all projects with IDs and names.

#### GET /api/tools/document-types

Returns all document types with metadata and aliases.

#### GET /api/tools/document-types/{type_id}

Returns detailed information for a specific document type.

#### GET /api/tools/search-strategies

Returns available search strategies for query configuration. Used by UI for strategy selection.

#### GET /api/tools/inference-options

Returns ML inference capabilities and options. Used by UI for inference configuration.

### 📊 Statistics Endpoints

See detailed documentation above for comprehensive endpoint information:

- **GET /api/stats/processing** - Processing statistics for all projects
- **GET /api/stats/processing/{project_id}** - Detailed processing logs for a specific project  
- **GET /api/stats/summary** - High-level processing summary across the entire system

### 🚀 Missing Endpoints (Agentic Workflows)

The following endpoints are designed for agentic workflows where AI clients perform intelligent operations:

- `POST /api/inference-search` - Smart search with ML inference
- `POST /api/agentic-search` - Multi-strategy intelligent search  
- `GET /api/capabilities` - Complete API metadata
- `POST /api/suggest-filters` - AI-powered filter recommendations
- `GET /api/stats/health[/{id}]` - Project health analysis

### Response Patterns

All endpoints follow consistent response patterns:

- **Success**: JSON with `result` wrapper and performance `metrics`
- **Error**: JSON with `error` field and appropriate HTTP status codes
- **Caching**: Discovery endpoints cached for 1 hour
- **Logging**: Comprehensive request/response logging for debugging

### Performance Features

- **Caching**: 1-hour TTL for discovery and metadata endpoints
- **Metrics**: Detailed timing information in all responses
- **Error Handling**: Comprehensive error catching with fallback responses
- **CORS**: Configurable CORS support for web applications

## Configuration

### Azure OpenAI Configuration

The service now supports Azure OpenAI with private endpoint access. Configuration includes:

| Variable | Description | Default |
|----------|-------------|---------|
| LLM_PROVIDER | LLM provider selection | openai |
| AZURE_OPENAI_API_KEY | Azure OpenAI API key | - |
| AZURE_OPENAI_ENDPOINT | Azure OpenAI endpoint URL | - |
| AZURE_OPENAI_DEPLOYMENT | Model deployment name (e.g., gpt-4, gpt-35-turbo) | - |
| AZURE_OPENAI_API_VERSION | API version for Azure OpenAI endpoints | 2024-02-15-preview |

### Private Endpoint Access

The service is configured to access Azure OpenAI through a private endpoint, ensuring secure communication within the Azure virtual network. This requires:

1. The application must be deployed within the same VNet as the Azure OpenAI private endpoint
2. DNS resolution must be configured to resolve the privatelink.openai.azure.com domain
3. Network security groups must allow traffic between the application and the private endpoint

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| VECTOR_SEARCH_API_URL | URL for the external vector search service |  |
| LLM_HOST | Host address for the LLM service |  |
| LLM_MODEL | Ollama model to use | qwen2.5:0.5b |
| LLM_TEMPERATURE | Temperature parameter for LLM generation | 0.3 |
| LLM_MAX_TOKENS | Maximum tokens for LLM response | 150 |
| LLM_MAX_CONTEXT_LENGTH | Maximum context length for LLM | 4096 |
| LLM_SYSTEM_MESSAGE | System prompt for the LLM (system message for Azure OpenAI, controls LLM behavior and tone) | 'You are an AI assistant for employees in FAQ system. Your task is to synthesize coherent and helpful answers based on the given query and relevant context from a knowledge database.' |
| S3_BUCKET | Name of the S3 bucket containing documents |  |
| S3_ACCESS_KEY_ID | AWS access key ID for S3 access |  |
| S3_SECRET_ACCESS_KEY | AWS secret access key for S3 access |  |
| S3_HOST | S3 endpoint host |  |
| S3_REGION | AWS region for S3 bucket |  |
| S3_SERVICE | Service name (default: s3) | s3 |

## Extendability

The Search API is designed to be extensible in the following ways:

1. **LLM Provider Architecture**: The service uses a modular synthesizer architecture:
   - Abstract `LLMSynthesizer` base class defines the interface
   - `OllamaSynthesizer` implements local LLM integration
   - `AzureOpenAISynthesizer` implements Azure OpenAI integration
   - Additional providers can be added by implementing the base class

2. **Customized Prompts**: The prompt template can be modified in the `LLMSynthesizer` class to adjust how the LLM interprets and responds to queries.

3. **Response Formatting**: Each synthesizer implementation can customize response formatting while maintaining a consistent interface.

## Performance and Security Considerations

### Security Best Practices

1. API Key Management
   - Store API keys and secrets securely using environment variables or a secrets management service
   - Never commit API keys or sensitive credentials to version control
   - Rotate API keys periodically according to your security policy

2. Network Security
   - Use private endpoints for Azure OpenAI access to ensure traffic stays within your virtual network
   - Configure Network Security Groups (NSGs) to restrict traffic between application and services
   - Enable TLS/SSL for all external communications
   - Implement proper CORS policies to restrict cross-origin requests

3. Access Control
   - Implement authentication for all API endpoints
   - Use role-based access control (RBAC) to limit access to sensitive operations
   - Validate and sanitize all user inputs
   - Implement rate limiting to prevent abuse

### Performance Optimization

- The service collects detailed performance metrics at each step for monitoring and optimization
- Timeouts are configured for external service calls to prevent hanging requests
- Error handling ensures graceful degradation when services are unavailable
- Consider implementing caching for:
  - Frequently requested search queries
  - Document downloads from S3, especially for frequently accessed PDFs
  - Use appropriate cache headers for PDF downloads to enable browser caching

## Dependencies

Core Dependencies:

- **Flask**: Web framework for the REST API
- **Requests**: HTTP client for external service communication

LLM Provider Dependencies:

- **Ollama**: Integration with local LLMs for development
- **OpenAI**: Azure OpenAI client library for production

## Future Enhancements

- Response caching for frequently requested queries and agentic insights  
- Enhanced retry mechanisms with exponential backoff for LLM calls
- Performance optimizations and monitoring dashboards for agentic workflows
- Support for additional LLM providers (Claude, Gemini, etc.)
- Streaming responses for long-running queries and agentic processing
- Advanced query relevance validation with domain-specific rules
- Multi-step agentic reasoning for complex search scenarios

## Vector API & Agentic Search Implementation Status

### 🎉 **COMPLETE PARITY ACHIEVED!**

The Search API now provides **100% coverage** of the Vector API specification with intelligent LLM-powered agentic search functionality.

### Vector API Endpoint Coverage: ✅ 13/13 (100%)

| Vector API Endpoint | Our Implementation | Status |
|---------------------|-------------------|---------|
| **SEARCH ENDPOINTS** | | |
| `POST /api/vector-search` | `POST /api/search/query` | ✅ |
| `POST /api/document-similarity` | `POST /api/search/document-similarity` | ✅ |
| **TOOLS/DISCOVERY ENDPOINTS** | | |
| `GET /api/tools/projects` | `GET /api/tools/projects` | ✅ |
| `GET /api/tools/document-types` | `GET /api/tools/document-types` | ✅ |
| `GET /api/tools/document-types/{type_id}` | `GET /api/tools/document-types/{type_id}` | ✅ |
| `GET /api/tools/search-strategies` | `GET /api/tools/search-strategies` | ✅ |
| `GET /api/tools/inference-options` | `GET /api/tools/inference-options` | ✅ |
| `GET /api/tools/api-capabilities` | `GET /api/tools/api-capabilities` | ✅ |
| **STATS ENDPOINTS** | | |
| `GET /api/stats/processing` | `GET /api/stats/processing` | ✅ |
| `GET /api/stats/processing/{project_id}` | `GET /api/stats/processing/{project_id}` | ✅ |
| `GET /api/stats/summary` | `GET /api/stats/summary` | ✅ |
| **HEALTH ENDPOINTS** | | |
| `GET /healthz` | `GET /healthz` | ✅ |
| `GET /readyz` | `GET /readyz` | ✅ |

### Agentic Search Features: ✅ Production Ready

The Search API provides intelligent search functionality through direct LLM integration with multi-step parameter extraction.

#### Generation Services Implementation

**Essential Agentic Services:**

1. **Query Validator** - LLM-powered EAO relevance validation
2. **Parameter Extractor** - Multi-step AI-powered parameter extraction  
3. **Summarizer** - AI-powered response synthesis and document summarization

**Multi-Step Parameter Extraction:**

- **Step 1**: Project ID extraction with fuzzy matching
- **Step 2**: Document type extraction via comprehensive alias search  
- **Step 3**: Search strategy optimization and semantic query refinement

#### Vector API Coverage

The `VectorSearchClient` provides complete coverage of the Vector API specification through direct REST endpoints, supporting all search, discovery, and statistics operations needed by agentic search functionality.

### Recent Implementation Changes

#### **NEW**: API Capabilities Endpoint

- **Added**: `GET /api/tools/api-capabilities`
- **Resource**: `ApiCapabilities` class in `tools.py`
- **Service**: `StatsService.get_api_capabilities()` method
- **Client**: `VectorSearchClient.get_api_capabilities()` method
- **Features**: Provides complete API metadata with intelligent fallback capabilities

#### **Verified**: Health Endpoints Already Public

- **Confirmed**: `/healthz` and `/readyz` are public endpoints
- **Architecture**: Separate `HEALTH_BLUEPRINT` with URL_PREFIX = "/"
- **Alignment**: Endpoints match Vector API standards

#### **Updated**: Test Coverage

- **Added**: API capabilities test to `test-api.http`
- **Added**: Public health endpoint tests
- **Complete**: All 13 Vector API endpoints now testable

### Agentic Workflow Architecture

```text
User Request → [Search API] → [VectorSearchClient] → [Vector API]
                    ↓
         [Direct LLM Integration]
                    ↓
        [Multi-Step Parameter Extraction]
                    ↓
      [LLM-Powered Intelligence Services]
```

The Search API now serves as a **complete proxy and intelligent wrapper** around the Vector API, providing both direct access and AI-enhanced capabilities for optimal user experience.

## Agentic Architecture and Current API Status

### **Current Public API Endpoints**

#### **SEARCH ENDPOINTS**

- `POST /api/search/query` - Main search endpoint
  - Supports `agentic=true` flag for AI-powered extraction and optimization
  - Returns search results with optional agentic insights (relevance, filters, strategy)
- `POST /api/search/document-similarity` - Document similarity search

#### **TOOLS ENDPOINTS** (for metadata and agentic support)

- `GET /api/tools/projects` - Get available projects
- `GET /api/tools/document-types` - Get available document types  
- `GET /api/tools/search-strategies` - Get available search strategy options

#### **STATS ENDPOINTS**

- `GET /api/stats/*` - Various statistics endpoints

#### **HEALTH ENDPOINTS**

- `GET /healthz` - Health check endpoint
- Other operational endpoints

### **Removed Endpoints (Agentic - Internal Use Only)**

❌ **AGENTIC ENDPOINTS** (removed from public API)

- `/api/agentic/suggest-filters` - AI filter recommendations
- `/api/agentic/search-with-inference` - Search with AI inference  
- `/api/agentic/orchestrated-search` - Full agentic orchestration
- `/api/agentic/health` - Agentic health check

### **How Agentic Functionality Works Now**

The agentic functionality is **internalized** and only available through:

```json
POST /api/search/query
{
  "query": "For the South Anderson Mountain Resort project I want all letters that mention the 'Nooaitch Indian Band'",
  "agentic": true
}
```

**Agentic Mode Processing Flow:**

1. **🛡️ Query Relevance Validation** (NEW)
   - Uses LLM-powered query validation service
   - Validates if query is EAO/environmental assessment related
   - For non-relevant queries (e.g., "Who won the soccer world cup?"):
     - Returns helpful message explaining EAO scope
     - Prevents unnecessary processing
     - Includes confidence score and reasoning

2. **🔍 Multi-Step Parameter Extraction**
   - Uses direct LLM integration for AI-powered analysis
   - Step 1: Extracts project IDs with fuzzy matching
   - Step 2: Extracts document types via comprehensive alias search
   - Step 3: Optimizes search strategy and generates semantic query

3. **⚡ Search Strategy Optimization**
   - Uses direct LLM service integration
   - Recommends optimal search approach based on query type
   - Provides confidence scores and explanations

**Response includes:**

- Regular search results (for EAO-relevant queries)
- `query_relevance` section with:
  - `is_eao_relevant` (boolean)
  - `confidence` score
  - `reasoning` (array of explanations)
  - `recommendation` (proceed_with_search | inform_user_out_of_scope)
- `agentic_suggestions` section with:
  - `recommended_filters` (project_ids, document_type_ids, semantic_query)
  - `confidence` score
  - `entities_detected`
  - `recommendations`
  - `reasoning`
- Early exit responses for out-of-scope queries with helpful guidance

This approach keeps the agentic AI functionality internal while providing intelligent query validation and a clean public API surface.

### **Agentic Flow Architecture**

#### **1. Client Layer (`src/search_api/clients/`)**

**VectorSearchClient (`vector_search_client.py`)**

- **Purpose**: Direct HTTP communication with external vector search API
- **Used for**:
  - Primary search operations (`search()` method)
  - Document similarity search
  - Metadata retrieval (projects, document types)
- **Status**: ✅ **ACTIVELY USED** in both regular and agentic workflows

#### **2. Service Layer (`src/search_api/services/`)**

**SearchService (`search_service.py`)**

- **Uses**: `VectorSearchClient` for direct API calls
- **Agentic Integration**: Calls `AgenticService` when `agentic=true`

**AgenticService (`agentic_service.py`)**

- **Uses**: Direct LLM integration via generation services
- **Key capabilities**:
  - Multi-step parameter extraction
  - Query relevance validation
  - Response synthesis

#### **3. Generation Services Layer (`src/search_api/services/generation/`)**

#### **Factory Pattern Implementation**

- **LLMClientFactory**: Creates OpenAI or Ollama clients based on environment
- **ParameterExtractorFactory**: Creates parameter extraction services
- **QueryValidatorFactory**: Creates query validation services
- **SummarizerFactory**: Creates response synthesis services

#### **Core Services**

**Parameter Extractor (`parameter_extractor.py`)**

- **Multi-step extraction process**:
  - **Step 1**: Project ID extraction with fuzzy matching
  - **Step 2**: Document type extraction via comprehensive alias search
  - **Step 3**: Search strategy optimization and semantic query refinement
- **Fallback logic**: Robust keyword matching when LLM calls fail
- **Provider support**: Both OpenAI and Ollama implementations

**Query Validator (`query_validator.py`)**

- **Purpose**: LLM-powered EAO relevance validation
- **Features**: Confidence scoring and detailed reasoning
- **Early exit**: Prevents processing of out-of-scope queries

**Summarizer (`summarizer.py`)**

- **Purpose**: Response synthesis and document summarization
- **Integration**: Works with both OpenAI and Ollama
- **Features**: Context-aware response generation

### **Current Agentic Request Flow**

```text
1. POST /api/search/query (agentic=true)
   ↓
2. SearchService.get_documents_by_query()
   ↓  
3. AgenticService.get_filtered_search_recommendations()
   ↓
4. QueryValidator.validate_query_relevance()
   ↓
5. ParameterExtractor.extract_parameters() (multi-step)
   ↓ 
6. Direct LLM calls with fallback logic
   ↓
7. Return: {project_ids, document_type_ids, semantic_query, confidence, etc.}
   ↓
8. VectorSearchClient.search() with extracted parameters
   ↓
9. Summarizer.generate_response() for synthesis
   ↓
10. Return combined results with agentic insights
```

### **Key Architecture Benefits**

The agentic functionality uses **direct LLM integration** with:

- **Factory pattern** for provider-agnostic service creation
- **Multi-step parameter extraction** for improved accuracy
- **Comprehensive fallback logic** for reliability
- **Clean separation of concerns** between validation, extraction, and synthesis

This is a maintainable, efficient architecture that provides robust AI capabilities while keeping the codebase simple and testable.

## Deployment Guide

### Environment Configuration

The Search API supports multiple deployment environments with automatic configuration detection:

#### Local Development

- **Python Environment**: Virtual environment or system Python
- **Configuration**: `.env` file with OpenAI or Ollama settings
- **LLM Provider**: Configurable via `LLM_PROVIDER` environment variable

#### Container/Azure Deployment

- **Container Support**: Docker with proper environment variable configuration
- **Azure Integration**: App Service with managed identity support
- **Scaling**: Horizontal scaling with stateless architecture

### Deployment Environment Variables

Required configuration for different LLM providers:

#### OpenAI Configuration

```bash
LLM_PROVIDER=openai
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-01
```

#### Ollama Configuration

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### Factory Pattern Benefits

The architecture's factory pattern provides:

- **Provider Flexibility**: Easy switching between OpenAI and Ollama
- **Environment Adaptation**: Automatic configuration based on deployment context
- **Maintainability**: Clean separation between abstract interfaces and concrete implementations
- **Testability**: Easy mocking and unit testing of individual components

### Agentic Architecture Performance

- **Multi-step Extraction**: Optimized for accuracy over speed
- **Caching**: Intelligent caching of frequently-accessed metadata
- **Fallback Logic**: Robust error handling with keyword-based fallbacks
- **Parallel Processing**: Where possible, concurrent LLM calls for improved performance

This architecture provides a robust, scalable foundation for agentic search functionality.

#### Option 1: Azure App Service (Container) - Recommended

**Environment Variables:**

```bash
# Required
VECTOR_SEARCH_API_URL=https://your-vector-api.azurewebsites.net/api
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Optional - Auto-detected
ENVIRONMENT=azure
LOG_LEVEL=INFO
```

**Container Deployment:**

```bash
# Build and deploy to Azure Container Registry
docker build -t epic-search-api:azure .
docker tag epic-search-api:azure your-registry.azurecr.io/epic-search-api:latest
docker push your-registry.azurecr.io/epic-search-api:latest
```

**App Service Configuration:**

- Runtime: Container
- Image source: Azure Container Registry  
- Minimum: P1V2 tier (1GB+ memory for LLM operations)
- Timeout: 300+ seconds for agentic workflows

#### Option 2: Direct Code Deployment

Deploy source code directly to Azure App Service:

- Runtime: Python 3.11
- Startup command: `gunicorn --bind 0.0.0.0:$PORT wsgi:application`

#### Option 3: Local Docker Testing

Test Azure behavior locally:

```bash
# Test with Azure environment settings
docker build -t epic-search-api:test .
docker run -p 8081:8080 --env-file .env.azure epic-search-api:test
```

### LLM Provider Integration

#### OpenAI/Azure OpenAI (Recommended for Production)

- Direct integration via official OpenAI SDK
- Built-in retry logic and error handling
- Optimized for cloud deployment
- Automatic scaling and reliability

#### Ollama (Local Development)

- Local LLM hosting for development
- Privacy-focused deployment option
- Consistent API interface via factory pattern
- Easy switching between providers

### Monitoring and Health Checks

- `GET /health` - Basic health check
- `GET /api/health` - Detailed health with LLM provider status  
- Application Insights integration for request tracing
- Structured logging for troubleshooting

### Migration and Testing

#### Staging Deployment

Use Azure App Service staging slots:

```bash
# Deploy to staging first
az webapp deployment slot create --name your-app --resource-group your-rg --slot staging
az webapp deploy --resource-group your-rg --name your-app --slot staging

# Test and swap when ready
az webapp deployment slot swap --resource-group your-rg --name your-app --slot staging
```

#### Environment Testing

The factory pattern ensures consistent behavior across environments:

- Local: Ollama integration with development settings
- Azure: OpenAI integration with production configuration
- Both use the same agentic API interface and extraction logic

### Troubleshooting

#### Common Issues

- **LLM not responding**: Check environment configuration:
  - **Local**: Verify Ollama is running and accessible
  - **Azure**: Verify Azure OpenAI endpoint and key configuration
- **Agentic mode not working**: Check LLM provider configuration and connectivity
- **High latency**: Check Vector API region and LLM provider performance:
  - **Local**: Ensure Ollama model is loaded and optimized
  - **Azure**: Check Azure OpenAI region proximity
- **Memory issues**: Scale up resources or optimize LLM usage patterns
- **Timeout errors**:
  - **Local**: Increase Ollama response timeout
  - **Azure**: Check Azure OpenAI rate limits and quotas
  - **Azure**: Increase App Service timeout settings

#### Environment-Specific Monitoring

**Local Development:**

- Monitor Ollama response times and model loading
- Check for CUDA/GPU utilization if available
- Verify local API endpoints are accessible

**Azure Production:**

- Monitor Azure OpenAI token usage and costs
- Set up alerts for error rates and response times
- Use Application Insights for detailed request tracing
- Implement proper CORS policies for production domains
