# EPIC Search MCP Server Documentation

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tool Reference](#tool-reference)
- [Azure Deployment](#azure-deployment)
- [Configuration Reference](#configuration-reference)
- [Health Monitoring](#health-monitoring)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Production Checklist](#production-checklist)

## Architecture Overview

### System Architecture

The MCP server acts as an intelligent layer that provides LLMs with tools to understand and interact with your Vector API. Your API client implements both direct API calls and intelligent orchestration using LLM recommendations.

#### Two Types of MCP Tools

**1. Direct API Tools (13 tools)**: Map 1:1 to your Vector API endpoints
**2. Intelligent Orchestration Tools (2 tools)**: Your API client implements using LLM + multiple Vector API calls

#### Agentic Flow

```text
[Website] → [Your API] → [LLM + MCP Server] → [Your API] → [Vector API] → [Database]
                    ↑                         ↑
                    │                         │
                    └─── Intelligent ─────────┘
                        Orchestration
```

### Role of Each Component

#### Your API Client (The Orchestrator)

- Receives requests from website
- **For Direct API Tools**: Maps MCP tool calls directly to Vector API endpoints
- **For Intelligent Tools**:
  - Uses LLM with MCP tools to analyze user query
  - Implements complex search strategies using multiple Vector API calls
  - Combines and enhances results
- Returns results to website

#### MCP Server (The Intelligence Layer)

- **Exposes Vector API capabilities** as structured tools for the LLM
- **Provides intelligence**: filter suggestions, strategy selection, etc.
- **Returns recommendations** - NOT actual data from Vector API
- **Your API implements Vector API client** to execute LLM recommendations

#### LLM (The Decision Maker)

- Uses MCP tools to understand Vector API capabilities
- Analyzes user queries for intent
- Recommends optimal search strategies and filters
- **Returns instructions** for your API to execute against Vector API

### Implementation Architecture

**Your API needs a Vector API client** that implements all endpoints referenced by MCP tools:

```python
# Your API implements Vector API client
class VectorAPIClient:
    def vector_search(self, query, project_ids=None, document_types=None, ...):
        return requests.post(f"{VECTOR_API_URL}/search", json={...})
    
    def find_similar_documents(self, document_id, max_results=10):
        return requests.post(f"{VECTOR_API_URL}/similarity", json={...})
    
    # ... all other endpoints that MCP tools reference
```

**MCP tools return instructions, not data**:

- `suggest_filters` → Returns recommended filters
- `vector_search` → Returns optimized search parameters
- `get_available_projects` → Returns project metadata for filtering

### Example Agentic Flow

**User Query**: *"Find environmental reports from coastal projects"*

1. **Website** → **Your API**: *"Find environmental reports from coastal projects"*
2. **Your API** → **LLM**: *"User wants environmental reports from coastal projects"*
3. **LLM** → **MCP Server** `suggest_filters`: *"environmental reports coastal projects"*
4. **MCP Server** → **LLM**: *"Recommended: project_ids=['coastal_proj_1'], document_types=['EIA']"*
5. **LLM** → **Your API**: *"Call vector_search with these optimized parameters..."*
6. **Your API** → **Vector API**: *Optimized search call*
7. **Vector API** → **Your API** → **Website**: *Enhanced results*

The MCP server **enables intelligent decision-making** but your API remains the **orchestrator** that actually calls the Vector API.

### Core Components

1. **MCP Server**: Exposes Vector API capabilities as standardized tools
2. **Search Tools**: Intelligent search orchestration and filtering
3. **Discovery Tools**: Dynamic API capability discovery
4. **Statistics Tools**: System health monitoring and analytics
5. **Health Check**: Container and service health monitoring

### Benefits

- **Intelligent Filtering**: AI-powered project and document type selection
- **Multi-Strategy Search**: Orchestrated search across multiple strategies
- **Dynamic Discovery**: Adaptive clients through API capability discovery
- **Format Consistency**: Maintains existing API response formats
- **Seamless Integration**: Drop-in replacement for direct API calls

## Tool Reference

The MCP server provides 15 tools divided into two categories:

### Direct API Tools (13 tools)

***These map directly to your Vector API endpoints***

#### Search Operations

#### `vector_search`

Maps to: `POST /api/vector-search`

Advanced two-stage hybrid search with comprehensive parameter control.

**Parameters:**

- `query` (string, required): Search query
- `project_ids` (array, optional): Filter by specific projects
- `document_types` (array, optional): Filter by document types
- `inference` (boolean, optional): Enable ML inference
- `search_strategy` (string, optional): Search strategy to use
- `max_results` (integer, optional): Maximum results to return

**Example:**

```json
{
  "query": "environmental impact assessment",
  "project_ids": ["proj_123", "proj_456"],
  "document_types": ["EIA", "ESA"],
  "inference": true,
  "max_results": 20
}
```

#### `find_similar_documents`

Find documents similar to a specific document using legacy endpoint.

**Parameters:**

- `document_id` (string, required): ID of reference document
- `max_results` (integer, optional): Maximum similar documents

#### `document_similarity_search`

Document-level embedding similarity search.

**Parameters:**

- `document_id` (string, required): Reference document ID
- `similarity_threshold` (float, optional): Minimum similarity score
- `max_results` (integer, optional): Maximum results

#### `search_with_auto_inference`

Smart search with automatic project and document type inference.

**Parameters:**

- `query` (string, required): Natural language search query
- `context` (string, optional): Additional context for inference

### Discovery & Intelligence

#### `get_available_projects`

Retrieve all available projects with metadata.

**Returns:** Array of project objects with IDs, names, and metadata.

#### `get_available_document_types`

Get document types with aliases and descriptions.

**Returns:** Array of document type objects with type codes and aliases.

#### `get_document_type_details`

Get detailed information for a specific document type.

**Parameters:**

- `document_type` (string, required): Document type code

#### `get_search_strategies`

Retrieve available search strategies and their capabilities.

**Returns:** Array of strategy objects with names and descriptions.

#### `get_inference_options`

Get available ML inference services and options.

**Returns:** Object describing inference capabilities and services.

#### `get_api_capabilities`

Complete API metadata discovery for adaptive clients.

**Returns:** Comprehensive API capability description.

### Agentic Operations

#### `suggest_filters`

AI-powered filter recommendations based on query analysis.

**Parameters:**

- `query` (string, required): Search query to analyze
- `context` (string, optional): Additional context

**Returns:** Recommended filters for projects and document types.

#### `agentic_search`

Multi-strategy intelligent search orchestration.

**Parameters:**

- `query` (string, required): Search query
- `strategies` (array, optional): Preferred search strategies
- `auto_filter` (boolean, optional): Enable automatic filtering

**Returns:** Orchestrated search results from multiple strategies.

### Statistics & Monitoring

#### `get_processing_stats`

Processing statistics and system health metrics.

**Parameters:**

- `project_ids` (array, optional): Filter by specific projects

**Returns:** Processing statistics with success/failure rates.

#### `get_project_details`

Detailed processing information for a specific project.

**Parameters:**

- `project_id` (string, required): Project identifier

#### `get_system_summary`

High-level system overview and health status.

**Returns:** System-wide health and processing summary.

## Azure Deployment

### Prerequisites

- Azure CLI installed and authenticated
- Docker installed locally
- Azure Container Registry or Docker Hub access

### Container Registry Setup

#### Option 1: Azure Container Registry

```bash
# Create ACR
az acr create --name youracr --resource-group your-rg --sku Basic

# Build and push
docker build -t epic-search-mcp-server .
docker tag epic-search-mcp-server youracr.azurecr.io/epic-search-mcp-server:latest
az acr login --name youracr
docker push youracr.azurecr.io/epic-search-mcp-server:latest
```

#### Option 2: Docker Hub

```bash
# Build and push
docker build -t epic-search-mcp-server .
docker tag epic-search-mcp-server yourusername/epic-search-mcp-server:latest
docker push yourusername/epic-search-mcp-server:latest
```

### App Service Deployment

#### Create Infrastructure

```bash
# Create resource group
az group create --name rg-epic-search --location canadacentral

# Create App Service plan
az appservice plan create \
  --name plan-epic-search \
  --resource-group rg-epic-search \
  --sku B1 \
  --is-linux

# Create App Service
az webapp create \
  --name epic-search-mcp-server \
  --resource-group rg-epic-search \
  --plan plan-epic-search \
  --deployment-container-image-name youracr.azurecr.io/epic-search-mcp-server:latest
```

#### Configure Application Settings

```bash
az webapp config appsettings set \
  --name epic-search-mcp-server \
  --resource-group rg-epic-search \
  --settings \
    VECTOR_SEARCH_API_URL="https://your-vector-api.azurewebsites.net/api" \
    MCP_SERVER_NAME="epic-search-tools" \
    LOG_LEVEL="INFO" \
    API_TIMEOUT="300" \
    ENVIRONMENT="production" \
    WEBSITES_PORT="8000" \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE="false"
```

### Azure Portal Configuration

#### Container Settings

- **Image Source**: Azure Container Registry or Docker Hub
- **Image**: `epic-search-mcp-server:latest`
- **Port**: `8000`
- **Startup Command**: Leave empty (uses Dockerfile CMD)

#### Health Check Settings

- **Path**: Custom health check via script
- **Timeout**: 30 seconds
- **Interval**: 60 seconds

## Configuration Reference

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VECTOR_SEARCH_API_URL` | string | Required | Vector API base URL |
| `MCP_SERVER_NAME` | string | `epic-search-tools` | MCP server identifier |
| `LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `API_TIMEOUT` | integer | `300` | API request timeout in seconds |
| `ENVIRONMENT` | string | `development` | Environment (development/production) |
| `WEBSITES_PORT` | integer | `8000` | Azure App Service port |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | boolean | `false` | Azure storage setting |

### Logging Configuration

#### Development

```python
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

- Human-readable console output
- Detailed debug information
- Color-coded log levels

#### Production

```python
LOG_LEVEL=INFO
ENVIRONMENT=production
```

- Structured JSON logging
- Application Insights integration
- Error tracking and monitoring

### API Configuration

#### Timeout Settings

- **Default**: 300 seconds (5 minutes)
- **Recommended Production**: 300 seconds
- **Development**: 60 seconds for faster feedback

#### Retry Logic

- Automatic retry on network failures
- Exponential backoff for rate limiting
- Circuit breaker for persistent failures

## Health Monitoring

### Health Check Script

The `health_check.py` script validates:

1. **Environment Configuration**: Required variables present
2. **Module Loading**: All MCP server modules load successfully
3. **HTTP Client**: HTTP client initialization
4. **Vector API Connectivity**: Optional endpoint validation

#### Usage

```bash
# Direct execution
python health_check.py

# Docker container
docker exec <container> python health_check.py

# Azure App Service
az webapp ssh --name epic-search-mcp-server --resource-group your-rg
python health_check.py
```

#### Health Check Output

**Success:**

```text
✅ MCP server modules loaded successfully
✅ HTTP client initialized successfully
✅ MCP Server health check passed
🎉 MCP Server is healthy
```

**Failure:**

```text
❌ VECTOR_SEARCH_API_URL not configured
💥 MCP Server health check failed
```

### Container Health Check

Docker health check runs every 30 seconds:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python health_check.py || exit 1
```

### Application Insights Integration

Enable Application Insights for comprehensive monitoring:

- **Performance Tracking**: Request/response times
- **Error Logging**: Exception tracking and stack traces
- **Dependency Monitoring**: Vector API call monitoring
- **Custom Metrics**: Tool usage statistics

## Security

### Container Security

- **Non-root User**: Runs as dedicated `app` user
- **Minimal Base Image**: Python 3.12 slim for reduced attack surface
- **No Secrets in Image**: All configuration via environment variables
- **Read-only Filesystem**: Application files mounted read-only

### Network Security

- **HTTPS Ready**: Supports TLS termination at load balancer
- **Environment Isolation**: Production/development separation
- **API Authentication**: Supports Vector API authentication headers
- **CORS Configuration**: Configurable cross-origin policies

### Best Practices

1. **Secret Management**: Use Azure Key Vault for sensitive data
2. **Network Isolation**: Deploy in private subnet with VPN access
3. **Access Control**: Implement Azure AD authentication
4. **Audit Logging**: Enable Azure Monitor for compliance
5. **Regular Updates**: Keep dependencies updated

## Troubleshooting

### Common Issues

#### Health Check Failures

**Symptom**: Health check script fails
**Causes:**

- Missing `VECTOR_SEARCH_API_URL` environment variable
- Network connectivity issues
- Module import failures

**Solutions:**

```bash
# Check environment variables
az webapp config appsettings list --name epic-search-mcp-server --resource-group your-rg

# Test connectivity
curl -f https://your-vector-api.azurewebsites.net/api/health

# Check logs
az webapp log tail --name epic-search-mcp-server --resource-group your-rg
```

#### Container Startup Issues

**Symptom**: Container fails to start
**Causes:**

- Port binding conflicts
- Memory/CPU constraints
- Invalid environment configuration

**Solutions:**

```bash
# Check container status
az webapp show --name epic-search-mcp-server --resource-group your-rg

# Review startup logs
az webapp log download --name epic-search-mcp-server --resource-group your-rg

# Test locally
docker run --rm -e VECTOR_SEARCH_API_URL=test epic-search-mcp-server python health_check.py
```

#### MCP Tool Failures

**Symptom**: Tools not responding or returning errors
**Causes:**

- Vector API endpoint changes
- Authentication failures
- Network timeouts

**Solutions:**

```bash
# Test Vector API directly
curl -H "Content-Type: application/json" \
  -d '{"query":"test"}' \
  https://your-vector-api.azurewebsites.net/api/search

# Check tool availability
python -c "from src.mcp_server.tools.search_tools import *; print('Tools loaded')"

# Increase timeout
az webapp config appsettings set \
  --name epic-search-mcp-server \
  --resource-group your-rg \
  --settings API_TIMEOUT=600
```

### Debug Commands

#### Azure CLI Debugging

```bash
# Application logs
az webapp log tail --name epic-search-mcp-server --resource-group your-rg

# Configuration review
az webapp config show --name epic-search-mcp-server --resource-group your-rg

# SSH access
az webapp ssh --name epic-search-mcp-server --resource-group your-rg

# Restart service
az webapp restart --name epic-search-mcp-server --resource-group your-rg
```

#### Local Development

```bash
# Test with debug logging
LOG_LEVEL=DEBUG python main.py

# Test individual tools
python -c "
from src.mcp_server.tools.search_tools import vector_search
result = vector_search('test query')
print(result)
"

# Validate environment
python -c "
import os
print('API URL:', os.getenv('VECTOR_SEARCH_API_URL'))
print('Log Level:', os.getenv('LOG_LEVEL'))
"
```

## Production Checklist

### Pre-Deployment

- [ ] **Environment Variables**: All required variables configured
- [ ] **Container Build**: Docker image builds successfully
- [ ] **Health Check**: Health script passes with valid configuration
- [ ] **Security Review**: No secrets in image, non-root user configured
- [ ] **Resource Planning**: Appropriate App Service plan selected

### Deployment

- [ ] **Image Push**: Container image pushed to registry
- [ ] **App Service**: Service created with correct configuration
- [ ] **Environment Config**: All variables set in Azure Portal
- [ ] **Health Monitoring**: Health checks enabled and passing
- [ ] **Log Stream**: Logging configured and accessible

### Post-Deployment

- [ ] **Functional Testing**: All 16 tools accessible and working
- [ ] **Performance Testing**: Response times within acceptable limits
- [ ] **Error Monitoring**: No critical errors in logs
- [ ] **Vector API Integration**: Successful communication with backend
- [ ] **Documentation**: Deployment documented and team informed

### Monitoring Setup

- [ ] **Application Insights**: Enabled and collecting telemetry
- [ ] **Alert Rules**: Critical error alerts configured
- [ ] **Dashboard**: Monitoring dashboard created
- [ ] **Log Retention**: Log retention policy configured
- [ ] **Health Notifications**: Health check failure alerts set up

### Success Criteria

- ✅ Container builds and deploys without errors
- ✅ Health check passes consistently
- ✅ All 16 MCP tools are accessible
- ✅ Vector API connectivity confirmed
- ✅ Production logging and monitoring active
- ✅ No security vulnerabilities identified
- ✅ Performance meets requirements
- ✅ Documentation complete and accurate
