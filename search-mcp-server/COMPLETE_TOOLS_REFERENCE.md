# Complete MCP Tools Reference for Your API Client

## Overview

Your API client needs to implement Vector API endpoints that correspond to these **15 MCP tools**. The tools fall into two categories:

1. **Direct API Tools (13 tools)**: Map directly to your Vector API endpoints
2. **Intelligent Orchestration Tools (2 tools)**: Your API client implements these using LLM + MCP recommendations + multiple Vector API calls

## Architecture Flow

```text
User Query → Your API Client → LLM + MCP Server → Your API Client → Vector API Endpoints → Results
```

## Complete Tool List

### 🔍 Direct API Search Operations (4 tools)

#### 1. `vector_search`

**Purpose**: Advanced two-stage hybrid search with comprehensive parameters
**Your API Endpoint**: `POST /api/vector-search`

```json
{
  "name": "vector_search",
  "description": "Perform vector similarity search through documents with advanced parameters",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query to find relevant documents"
      },
      "project_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional list of project IDs to filter by"
      },
      "document_type_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional list of document type IDs to filter by"
      },
      "inference": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["PROJECT", "DOCUMENTTYPE"]
        },
        "description": "Optional inference types to enable for intelligent filtering"
      },
      "ranking": {
        "type": "object",
        "properties": {
          "minScore": {"type": "number", "description": "Minimum relevance score threshold"},
          "topN": {"type": "integer", "description": "Maximum number of results to return"}
        },
        "description": "Optional ranking configuration"
      },
      "search_strategy": {
        "type": "string",
        "enum": [
          "HYBRID_SEMANTIC_FALLBACK",
          "HYBRID_KEYWORD_FALLBACK", 
          "SEMANTIC_ONLY",
          "KEYWORD_ONLY",
          "HYBRID_PARALLEL"
        ],
        "description": "Search strategy to use (default: HYBRID_SEMANTIC_FALLBACK)"
      }
    },
    "required": ["query"]
  }
}
```

#### 2. `find_similar_documents`

**Purpose**: Legacy document similarity endpoint
**Your API Endpoint**: `POST /api/document-similarity`

```json
{
  "name": "find_similar_documents",
  "description": "Find documents similar to a specific document using vector similarity",
  "inputSchema": {
    "type": "object",
    "properties": {
      "document_id": {
        "type": "string",
        "description": "ID of the document to find similarities for"
      },
      "project_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional list of project IDs to filter by"
      },
      "limit": {
        "type": "integer",
        "default": 10,
        "maximum": 50,
        "description": "Maximum number of similar documents to return"
      }
    },
    "required": ["document_id"]
  }
}
```

#### 3. `search_with_auto_inference`

**Purpose**: Smart search with ML inference
**Implementation**: Your API client implements using LLM analysis + `POST /api/vector-search`

```json
{
  "name": "search_with_auto_inference",
  "description": "Smart search that automatically determines best projects and document types based on query",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query - the system will intelligently determine relevant projects and document types"
      },
      "confidence_threshold": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.5,
        "description": "Confidence threshold for automatic filtering"
      },
      "max_results": {
        "type": "integer",
        "default": 10,
        "maximum": 50,
        "description": "Maximum number of results to return"
      }
    },
    "required": ["query"]
  }
}
```

#### 4. `get_available_projects`

**Purpose**: Project discovery for filtering
**Your API Endpoint**: `GET /api/tools/projects`

```json
{
  "name": "get_available_projects",
  "description": "Get list of available projects for filtering search results",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "description": "No parameters needed - returns all available projects"
  }
}
```

#### 5. `get_available_document_types`

**Purpose**: Document type discovery with aliases
**Your API Endpoint**: `GET /api/tools/document-types`

```json
{
  "name": "get_available_document_types", 
  "description": "Get list of available document types for filtering search results",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "description": "No parameters needed - returns all document types with metadata and aliases"
  }
}
```

#### 6. `get_document_type_details`

**Purpose**: Specific document type information
**Your API Endpoint**: `GET /api/tools/document-types/{document_type_id}`

```json
{
  "name": "get_document_type_details",
  "description": "Get detailed information about a specific document type",
  "inputSchema": {
    "type": "object",
    "properties": {
      "document_type_id": {
        "type": "string",
        "description": "The document type ID to get details for"
      }
    },
    "required": ["document_type_id"]
  }
}
```

## 🤖 Intelligent Orchestration Tools

***Your API client implements these using LLM + MCP tools + multiple Vector API calls***

### 7. `suggest_filters`

**Purpose**: AI-powered filter recommendations
**Implementation**: Your API client implements using LLM analysis + discovery tools

```json
{
  "name": "suggest_filters",
  "description": "Analyze a query and suggest optimal project and document type filters",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The user's search query to analyze for filter suggestions"
      },
      "context": {
        "type": "string",
        "description": "Additional context about what the user is looking for"
      },
      "confidence_threshold": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "default": 0.6,
        "description": "Minimum confidence level for filter suggestions"
      }
    },
    "required": ["query"]
  }
}
```

#### 8. `get_search_strategies`

**Purpose**: Available search strategies discovery
**Your API Endpoint**: `GET /api/tools/search-strategies`

```json
{
  "name": "get_search_strategies",
  "description": "Get all available search strategies (semantic, keyword, hybrid, metadata) with their capabilities",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

#### 9. `get_inference_options`

**Purpose**: ML inference services discovery
**Your API Endpoint**: `GET /api/tools/inference-options`

```json
{
  "name": "get_inference_options",
  "description": "Get available ML inference services (document type, project classification) with capabilities",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

#### 10. `get_api_capabilities`

**Purpose**: Complete API metadata discovery
**Your API Endpoint**: `GET /api/tools/api-capabilities`

```json
{
  "name": "get_api_capabilities",
  "description": "Complete API metadata and endpoint discovery for dynamic client generation",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

#### 11. `document_similarity_search`

**Purpose**: Document-level embedding similarity
**Your API Endpoint**: `POST /api/document-similarity`

```json
{
  "name": "document_similarity_search",
  "description": "Find documents similar to a specific document using document-level embeddings",
  "inputSchema": {
    "type": "object",
    "properties": {
      "document_id": {
        "type": "string",
        "description": "The document ID to find similar documents for"
      },
      "project_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional list of project IDs to filter similar documents by"
      },
      "limit": {
        "type": "integer",
        "default": 10,
        "maximum": 50,
        "description": "Maximum number of similar documents to return"
      }
    },
    "required": ["document_id"]
  }
}
```

#### 12. `agentic_search`

**Purpose**: Multi-strategy intelligent search orchestration
**Implementation**: Your API client implements using LLM + multiple search strategies

```json
{
  "name": "agentic_search",
  "description": "Intelligent search designed for agentic mode - combines multiple search strategies and provides comprehensive results",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query from the user"
      },
      "context": {
        "type": "string", 
        "description": "Additional context about what the user is looking for"
      },
      "user_intent": {
        "type": "string",
        "enum": [
          "find_documents",
          "find_similar", 
          "explore_topic",
          "get_overview",
          "specific_lookup"
        ],
        "description": "The detected user intent to guide search strategy"
      },
      "max_results": {
        "type": "integer",
        "default": 15,
        "maximum": 50,
        "description": "Maximum number of results to return"
      },
      "include_stats": {
        "type": "boolean",
        "default": false,
        "description": "Whether to include processing statistics in the response"
      }
    },
    "required": ["query"]
  }
}
```

### 📊 Statistics Operations (3 tools)

#### 13. `get_processing_stats`

**Purpose**: Processing statistics and health metrics
**Your API Endpoint**: `GET /api/stats/processing` (with optional `?project_id=id` query parameter)

```json
{
  "name": "get_processing_stats",
  "description": "Get processing statistics for projects including successful, failed, and skipped file counts",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_id": {
        "type": "string",
        "description": "Optional project ID to filter stats. If not provided, returns stats for all projects"
      }
    }
  }
}
```

#### 14. `get_project_details`

**Purpose**: Detailed project processing information
**Your API Endpoint**: `GET /api/stats/processing/{project_id}`

```json
{
  "name": "get_project_details",
  "description": "Get detailed processing logs and information for a specific project",
  "inputSchema": {
    "type": "object",
    "properties": {
      "project_id": {
        "type": "string",
        "description": "The project ID to get detailed information for"
      }
    },
    "required": ["project_id"]
  }
}
```

#### 15. `get_system_summary`

**Purpose**: High-level system overview
**Your API Endpoint**: `GET /api/stats/summary`

```json
{
  "name": "get_system_summary",
  "description": "Get high-level processing summary across the entire system",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

## Summary for Your API Implementation

### Required Vector API Endpoints (13 total)

**MCP Tools Available**: 15 total (12 search + 3 stats)

**Search Endpoints (2)**:

- `POST /api/vector-search` - vector_search
- `POST /api/document-similarity` - find_similar_documents, document_similarity_search

**Tools Endpoints (6)**:

- `GET /api/tools/projects` - get_available_projects
- `GET /api/tools/document-types` - get_available_document_types  
- `GET /api/tools/document-types/{type_id}` - get_document_type_details
- `GET /api/tools/search-strategies` - get_search_strategies
- `GET /api/tools/inference-options` - get_inference_options
- `GET /api/tools/api-capabilities` - get_api_capabilities

**Stats Endpoints (3)**:

- `GET /api/stats/processing` - get_processing_stats
- `GET /api/stats/processing/{project_id}` - get_project_details  
- `GET /api/stats/summary` - get_system_summary

**Health Endpoints (2)**:

- `GET /healthz` - Service health check
- `GET /readyz` - Service readiness check

### Key Implementation Notes

1. **MCP tools return recommendations** - your API executes them
2. **All schemas are exact** - implement parameters as specified
3. **Optional parameters** - handle gracefully when not provided
4. **Enum values** - strictly validate search strategies and inference types
5. **Array parameters** - support filtering by multiple projects/document types
6. **Error handling** - return appropriate HTTP status codes
