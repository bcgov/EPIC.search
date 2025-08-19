# EPIC Search## 🔄 Architecture Overview

```text
User Query → Your API Client → LLM + MCP Server → Your API Client → Vector API → Results
```

**Two Types of MCP Tools**:

1. **Direct API Tools**: Map 1:1 to Vector API endpoints
2. **Intelligent Tools**: Implemented by your API client using LLM + multiple Vector API calls

## 🛠️ Available MCP Tools (15 total)

A Model Context Protocol (MCP) server that provides intelligent access to the EPIC Search Vector API for LLM agents in agentic mode. The MCP server acts as an intelligence layer between LLMs and your Vector API, providing both direct API access and intelligent orchestration capabilities.

## 🚀 Features

- **Vector API Integration**: 15 MCP tools that interface with your 13 Vector API endpoints
- **Intelligent Orchestration**: Complex search strategies implemented by your API client using LLM recommendations
- **Discovery Tools**: Dynamic API capability discovery and document type lookups
- **Document Similarity**: Advanced document-level similarity search
- **Project Intelligence**: Smart project and document type filtering
- **Production Ready**: Containerized for Azure App Service deployment

## � Architecture Overview

```text
User Query → Your API Client → LLM + MCP Server → Your API Client → Vector API → Results
```

**Two Types of MCP Tools**:

1. **Direct API Tools**: Map 1:1 to Vector API endpoints
2. **Intelligent Tools**: Implemented by your API client using LLM + multiple Vector API calls

## �🛠️ Available MCP Tools (15 total)

### Direct API Tools (11 tools)

***These map directly to your Vector API endpoints***

**Search Operations (4 tools)**:

- `vector_search` - Maps to `POST /api/vector-search`
- `find_similar_documents` - Maps to `POST /api/document-similarity`
- `document_similarity_search` - Maps to `POST /api/document-similarity`
- `search_with_auto_inference` - Your API client implements using LLM + `POST /api/vector-search`

**Discovery & Tools (6 tools)**:

- `get_available_projects` - Maps to `GET /api/tools/projects`
- `get_available_document_types` - Maps to `GET /api/tools/document-types`
- `get_document_type_details` - Maps to `GET /api/tools/document-types/{type_id}`
- `get_search_strategies` - Maps to `GET /api/tools/search-strategies`
- `get_inference_options` - Maps to `GET /api/tools/inference-options`
- `get_api_capabilities` - Maps to `GET /api/tools/api-capabilities`

**Statistics (3 tools)**:

- `get_processing_stats` - Maps to `GET /api/stats/processing`
- `get_project_details` - Maps to `GET /api/stats/processing/{project_id}`
- `get_system_summary` - Maps to `GET /api/stats/summary`

### Intelligent Orchestration Tools (2 tools)

***Your API client implements these using LLM + MCP tools + multiple Vector API calls***

**Agentic Intelligence (2 tools)**:

- `suggest_filters` - Your API client implements using LLM analysis + discovery tools
- `agentic_search` - Your API client implements using LLM + multiple search strategies

## � Quick Start

### Local Development

```bash
# Clone and setup
git clone <repo-url>
cd search-mcp-server

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp sample.env .env
# Edit .env with your VECTOR_SEARCH_API_URL

# Run the server
python main.py
```

### Docker

```bash
# Build and run
docker build -t epic-search-mcp-server .
docker run -p 8000:8000 \
  -e VECTOR_SEARCH_API_URL=https://your-vector-api.azurewebsites.net/api \
  epic-search-mcp-server
```

### Docker Compose

```bash
cp sample.env .env
# Edit .env with your settings
docker-compose up -d
```

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `VECTOR_SEARCH_API_URL` | Vector API base URL (required) |
| `LOG_LEVEL` | Logging level (default: INFO) |
| `ENVIRONMENT` | Environment (development/production) |

### Health Endpoints

The service provides standard operational endpoints:

- `GET /healthz` - Basic health check (service alive)
- `GET /readyz` - Readiness check (ready to serve traffic)  
- `GET /livez` - Liveness check (should restart if failing)
- `GET /metrics` - Basic service metrics

## 🎯 Usage in Agentic Mode

Your API can toggle between modes:

## Normal Mode (Direct)

```text
[Website] → [Your API] → [Vector API] → [Database]
```

## Agentic Mode (Intelligent)

```text
[Website] → [Your API] → [LLM + MCP Server] → [Vector API] → [Database]
```

The MCP server provides LLMs with intelligent decision-making capabilities for search strategy selection, filtering, and API discovery.

## 📚 Documentation

For detailed information, see [DOCUMENTATION.md](DOCUMENTATION.md):

- Complete tool reference
- Azure deployment guide
- Architecture details
- Troubleshooting
- Production checklist

## 📝 License

Government of British Columbia

## Integration with Search API

This MCP server is designed to work alongside the main EPIC Search API. When the search API receives a request with `go_agentic=true`, it can:

1. Spawn an LLM agent
2. Connect the agent to this MCP server
3. Let the agent use tools to explore and answer the query
4. Return the agent's comprehensive analysis

## Development

### Adding New Tools

1. Create tool definition in appropriate tool class (`SearchTools` or `StatsTools`)
2. Implement the handler method
3. Add to the tool routing in the main server

### Testing

```bash
# Run tests
pytest

# Test individual tools
python -c "from mcp_server.tools.search_tools import SearchTools; print('Tools loaded')"
```

## API Compatibility

The MCP server maintains full compatibility with the vector search API's current interface:

- **Search Endpoint**: `/vector-search` (POST)
- **Similarity Endpoint**: `/vector-search/similar` (POST)  
- **Stats Endpoints**: `/stats/processing`, `/stats/project/{id}`, `/stats/summary`

All existing parameters and response formats are preserved and enhanced with agent-friendly summaries.
