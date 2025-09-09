# Complete MCP Tools Reference

## Overview

The EPIC Search MCP server provides **4 essential tools** focused on intelligent search and discovery:

1. **Connection Test Tool**: `echo_test` - MCP server connectivity verification
2. **Query Validation Tool**: `check_query_relevance` - EAO relevance validation  
3. **Primary Agentic Tool**: `suggest_filters` - AI-powered filter recommendations
4. **Search Strategy Tool**: `suggest_search_strategy` - AI-powered search strategy recommendations

## MCP Server Types

### 🎯 Production MCP Server (`mcp_server.py`)

- **Used by**: Flask API in local development and production
- **Communication**: JSON-RPC via stdin/stdout (subprocess mode locally) or direct integration (containers)
- **Tools**: Full set of 4 production tools listed above
- **Purpose**: Primary server for all agentic workflows

### 🔧 Standalone MCP Server (`standalone_mcp_server.py`)

- **Used by**: Manual testing and protocol debugging only
- **Communication**: JSON-RPC via stdin/stdout
- **Tools**: Single `test_echo` tool for basic connectivity testing
- **Purpose**: Development tool for testing MCP protocol compliance and debugging communication issues
- **Usage**: Run directly via `python standalone_mcp_server.py` for manual JSON-RPC testing

## Architecture Flow

```text
User Query → Flask API → MCPClient → MCP Server (mcp_server.py) → SearchTools → Vector API
```

## Tools Reference

### 🔌 CONNECTION TEST TOOL

#### `echo_test`

**Purpose**: Simple connectivity test to verify MCP server is responding correctly

**Usage**: Used for health checks and debugging MCP server communication

```json
{
  "name": "echo_test",
  "description": "Simple echo test to verify MCP server connectivity",
  "inputSchema": {
    "type": "object",
    "properties": {
      "message": {
        "type": "string",
        "description": "Message to echo back"
      }
    },
    "required": ["message"]
  }
}
```

**Sample Response**:

```json
{
  "success": true,
  "echoed_message": "Hello MCP Server",
  "server": "EPIC Search MCP Server",
  "tool": "echo_test",
  "timestamp": "1234567890.123"
}
```

### ✅ QUERY VALIDATION TOOL ⭐

#### `check_query_relevance`

**Purpose**: Validates whether a user query is relevant to EAO (Environmental Assessment Office) and environmental assessments before processing

**Usage**: Called upfront in agentic mode to prevent processing of completely unrelated queries (e.g., sports, entertainment, general knowledge questions)

```json
{
  "name": "check_query_relevance", 
  "description": "Check if a query is relevant to EAO (Environmental Assessment Office) and environmental assessments",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The user's query to check for EAO relevance"
      },
      "context": {
        "type": "string", 
        "description": "Additional context about the query"
      }
    },
    "required": ["query"]
  }
}
```

**Sample Response**:

```json
{
  "tool": "check_query_relevance",
  "query": "Who won the soccer world cup?",
  "is_eao_relevant": false,
  "confidence": 0.9,
  "reasoning": ["Non-EAO indicators detected: soccer, world cup", "No environmental assessment keywords found"],
  "recommendation": "inform_user_out_of_scope",
  "suggested_response": "I'm designed to help with Environmental Assessment Office (EAO) related queries about environmental assessments, projects, and regulatory processes in British Columbia. Your question appears to be outside this scope. Please ask about environmental assessments, projects under review, or EAO processes."
}
```

### �🔍 PRIMARY AGENTIC TOOL ⭐

#### `suggest_filters`

**Purpose**: AI-powered analysis of user queries to recommend optimal project and document type filters

**Usage**: This is the main tool used in agentic mode to intelligently extract project IDs and document types from natural language queries.

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

#### `suggest_search_strategy`

**Purpose**: AI-powered analysis of user queries to recommend optimal search strategy

**Usage**: This tool analyzes query characteristics (specificity, complexity, intent) and recommends the best search strategy for optimal results.

```json
{
  "name": "suggest_search_strategy",
  "description": "Analyze a query and recommend the optimal search strategy based on query characteristics",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The user's search query to analyze for strategy recommendation"
      },
      "context": {
        "type": "string", 
        "description": "Additional context about the search"
      },
      "user_intent": {
        "type": "string",
        "description": "User intent (e.g., 'find_documents', 'explore_topic', 'specific_lookup')"
      }
    },
    "required": ["query"]
  }
}
```

**Strategy Types**:

- `EXACT_MATCH`: For specific IDs, codes, or precise terms
- `KEYWORD_ONLY`: For simple keyword searches, specific terminology
- `SEMANTIC_ONLY`: For conceptual searches, natural language questions
- `DOCUMENT_ONLY`: For generic document requests like "all correspondence", "all reports"
- `HYBRID_SEMANTIC_FALLBACK`: General searches needing precision and recall
- `HYBRID_KEYWORD_FALLBACK`: Mix of specific and general terms
- `HYBRID_PARALLEL`: Comprehensive results with multiple approaches

**Enhanced Generic Document Detection**:

The tool now intelligently detects generic document requests with patterns like:

- "I want all the correspondence"
- "Give me all reports"
- "Show me all documents for project X"
- "Find all emails about [topic]"

When such patterns are detected, it recommends `DOCUMENT_ONLY` strategy for optimal results.

**Note**: The discovery tools `get_available_projects` and `get_available_document_types` are available in the SearchTools class but are **not exposed** through the MCP server. The MCP server focuses on the core agentic workflow tools while these discovery functions are handled directly by the Flask API endpoints.

## Implementation Notes

- **Caching**: Project, document type, and search strategy mappings are cached for 1 hour to improve performance
- **Fallback**: When MCP server is unavailable, fallback responses are provided
- **Error Handling**: Robust error handling with detailed logging for debugging

## Usage in Agentic Mode

The typical flow is:

1. User sends query with `agentic: true`
2. **Flask API calls `check_query_relevance` via MCP first (LLM-powered validation)**
3. **If query is not EAO-relevant, return early with informative message**
4. If query is relevant, Flask API calls `suggest_filters` and `suggest_search_strategy` via MCP
5. MCP server uses cached project/document type/strategy data with LLM analysis
6. Returns intelligent filter and strategy suggestions with confidence scores
7. Flask API calls the Vector Search API directly with the suggested parameters
8. Results are processed and synthesized for the final response

**Available MCP Tools in Production**:

- ✅ `echo_test` - Connectivity verification
- ✅ `check_query_relevance` - EAO relevance validation  
- ✅ `suggest_filters` - AI-powered filter recommendations
- ✅ `suggest_search_strategy` - AI-powered search strategy recommendations

**Tools Available in SearchTools Class (not exposed via MCP)**:

- 🔧 `get_available_projects` - Available via Flask API endpoints
- 🔧 `get_available_document_types` - Available via Flask API endpoints

## LLM Integration Details

**Query Relevance Validation:**

- **Primary Method**: Uses LLM through MCP tools for sophisticated analysis
- **Fallback Method**: Rule-based keyword matching when LLM/MCP unavailable
- **Scope**: EAO/environmental assessment topics vs general knowledge/entertainment
- **Confidence Scoring**: Provides reasoning and confidence levels for decisions

**Filter and Strategy Suggestions:**

- **Primary Method**: LLM-powered analysis through MCP tools
- **Fallback Method**: Rule-based pattern matching and heuristics
- **Context Awareness**: Considers available projects, document types, and search strategies
- **Dynamic Adaptation**: Real-time metadata fetching and caching for optimal suggestions

This hybrid approach ensures reliable operation while leveraging LLM capabilities when available.
