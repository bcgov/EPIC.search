# Docker Development Setup

This guide explains how to set up the application for local development using Docker Compose.

## Quick Start

1. **Copy environment files:**

   ```bash
   cp .env.example .env
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```

2. **Update the `.env` file with your actual values:**

   ```bash
   # Required: Update these with your actual Azure OpenAI credentials
   AZURE_OPENAI_API_KEY=your-actual-api-key-here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   
   # Required: Update with your Vector API URL
   VECTOR_API_URL=http://your-vector-api:8080/api
   ```

3. **Start the services:**

   ```bash
   docker-compose up -d
   ```

4. **Access the application:**

   - Search API: http://localhost:8082
   - Keycloak: http://localhost:8081
   - Database: localhost:54332 (PostgreSQL)

## File Structure

- `docker-compose.yml` - Base configuration (safe for source control)
- `docker-compose.override.yml` - Local development overrides (ignored by git)
- `.env` - Environment variables (ignored by git)
- `.env.example` - Template for environment variables (committed to git)

## Security Notes

- Never commit `.env` or `docker-compose.override.yml` files
- Use placeholder values in base configuration files
- Keep sensitive data in local override files only

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `sk-...` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://example.openai.azure.com` |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name | `gpt-4` |
| `VECTOR_API_URL` | Vector Search API URL | `http://localhost:8080/api` |
| `DB_USERNAME` | Database username | `search` |
| `DB_PASSWORD` | Database password | `search` |

## Troubleshooting

1. **Port conflicts:** Update port mappings in `.env` file
2. **Permission issues:** Ensure Docker has proper file access
3. **Network issues:** Check Docker network configuration

For more details, see the main [DOCUMENTATION.md](DOCUMENTATION.md) file.
