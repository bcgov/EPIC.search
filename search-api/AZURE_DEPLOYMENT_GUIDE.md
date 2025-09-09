# Azure App Service Deployment Guide

This guide covers deploying the EPIC Search API to Azure App Service with proper MCP integration.

## Architecture for Azure

### Environment Detection

The API automatically detects the deployment environment and adapts the MCP integration:

- **Local Development**: Uses subprocess MCP server (`python mcp_server.py`)
- **Azure App Service**: Uses direct integration (no subprocess)
- **Container Environments**: Uses direct integration for reliability

### MCP Integration Modes

#### 1. Direct Integration Mode (Azure/Container)

- MCP tools are imported directly into the Flask app
- No subprocess communication
- Better performance and reliability in containers
- Automatic failover and retry logic

#### 2. Subprocess Mode (Local Development)

- Spawns separate MCP server process
- Uses stdio communication
- Maintains development flexibility

## Azure App Service Configuration

### Environment Variables

Set these in your Azure App Service Configuration:

```bash
# Required
VECTOR_API_URL=https://your-vector-api.azurewebsites.net/api
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Optional
ENVIRONMENT=azure
MCP_MODE=direct
LOG_LEVEL=INFO
CORS_ORIGIN=https://your-frontend.azurewebsites.net
```

### Deployment Options

#### Option 1: Container Deployment (Recommended)

Deploy using the provided Dockerfile:

1. **Build and push container**:

   ```bash
   # Build the image
   docker build -t epic-search-api:azure .
   
   # Tag for Azure Container Registry
   docker tag epic-search-api:azure your-registry.azurecr.io/epic-search-api:latest
   
   # Push to ACR
   docker push your-registry.azurecr.io/epic-search-api:latest
   ```

2. **Configure App Service**:
   - Runtime: Container
   - Image source: Azure Container Registry
   - Image: `your-registry.azurecr.io/epic-search-api:latest`

#### Option 2: Code Deployment

Deploy source code directly to App Service:

1. **Configure runtime**:
   - Runtime: Python 3.11
   - Startup command: `gunicorn --bind 0.0.0.0:$PORT wsgi:application`

2. **Deploy code**:

   ```bash
   # Using Azure CLI
   az webapp deploy --resource-group your-rg --name your-app --src-path .
   ```

### Performance Considerations

#### Scaling

- **Horizontal**: App Service can auto-scale based on CPU/memory
- **Vertical**: Use P1V2 or higher for production workloads
- **Cold start**: Direct integration reduces cold start time vs subprocess

#### Resource Limits

- **Memory**: Minimum 1GB recommended for LLM operations
- **CPU**: Multi-core beneficial for concurrent requests
- **Timeout**: Set to 300+ seconds for complex agentic workflows

### Monitoring and Diagnostics

#### Application Insights

Enable Application Insights for monitoring:

- Request traces
- Dependency calls (Vector API, Azure OpenAI)
- Exception tracking
- Performance metrics

#### Health Checks

The API includes health check endpoints:

- `GET /health` - Basic health check
- `GET /api/health` - Detailed health with MCP status

#### Logging

Structured logging with appropriate levels:

- `INFO`: Normal operations
- `WARNING`: Fallback scenarios
- `ERROR`: Failed operations
- `DEBUG`: Detailed troubleshooting (dev only)

## Troubleshooting

### Common Issues

#### MCP Tools Not Working

- **Symptom**: Agentic mode returns fallback responses
- **Solution**: Check that `MCP_MODE=direct` is set
- **Verification**: Check logs for "Container environment detected"

#### High Latency

- **Symptom**: Slow response times
- **Cause**: Network latency to Vector API or Azure OpenAI
- **Solution**:
  - Ensure Vector API is in same region
  - Use appropriate Azure OpenAI region
  - Implement caching for repeated calls

#### Memory Issues

- **Symptom**: App restarts or out-of-memory errors
- **Cause**: Large LLM contexts or concurrent requests
- **Solution**:
  - Scale up App Service plan
  - Implement request queuing
  - Optimize LLM token usage

### Environment-Specific Testing

#### Local Container Testing

Test Azure behavior locally:

```bash
# Build and run container with Azure environment
docker build -t epic-search-api:test .
docker run -p 8081:8080 --env-file .env.azure epic-search-api:test
```

#### Azure Test Deployment

Use staging slots for testing:

```bash
# Create staging slot
az webapp deployment slot create --name your-app --resource-group your-rg --slot staging

# Deploy to staging
az webapp deploy --resource-group your-rg --name your-app --slot staging --src-path .

# Test and swap
az webapp deployment slot swap --resource-group your-rg --name your-app --slot staging --target-slot production
```

## Security Considerations

### Secrets Management

- Use Azure Key Vault for sensitive configuration
- Enable Managed Identity for secure access
- Rotate keys regularly

### Network Security

- Configure Virtual Network integration if needed
- Use Private Endpoints for database connections
- Implement Web Application Firewall (WAF)

### Compliance

- Enable audit logging
- Configure data retention policies
- Implement proper CORS policies

## Cost Optimization

### App Service

- Use appropriate tier (P1V2 for production)
- Enable auto-scaling with proper thresholds
- Consider reserved instances for predictable workloads

### Dependencies

- Monitor Azure OpenAI token usage
- Implement caching to reduce API calls
- Use efficient prompt engineering

### Monitoring

- Set up cost alerts
- Monitor resource utilization
- Review and optimize regularly
