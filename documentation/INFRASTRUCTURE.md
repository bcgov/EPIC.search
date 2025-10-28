# Infrastructure & Deployment

## Azure Implementation

### Network Architecture

```mermaid
graph TB
    %% Azure Components
    WebUI["Web UI\n(VITE/NGINX)\nAzure App Service"]
    WebAPI["Web API\nPrivate Endpoint\nAzure App Service"]
    VectorAPI["Vector API\nPrivate Endpoint\nAzure App Service"]
    VectorDB["Vector Database\nAzure PostgreSQL\nFlexible Server"]
    LLM["LLM Service\n(OLLAMA or Azure OpenAI)\nConfiguration-based\nVM or Azure Service"]
    Embedder["Document Embedder\nVM"]
    
    %% NSG nodes
    FNSG["Frontend NSG"]
    ANSG["API NSG"]
    DNSG["Database NSG"]
    VNSG["VM NSG"]
    
    %% Azure-specific connections
    FNSG -.->|Secures| FSNET
    ANSG -.->|Secures| ASNET
    DNSG -.->|Secures| DSNET
    VNSG -.->|Secures| VSNET
    
    %% Azure Virtual Network Structure
    subgraph VNET["Azure Virtual Network"]
        subgraph FSNET["Frontend Subnet"]
            WebUI
        end
        subgraph ASNET["API Subnet"]
            WebAPI
            VectorAPI
        end
        subgraph DSNET["Database Subnet"]
            VectorDB
        end
        subgraph VSNET["VM Subnet"]
            LLM
            Embedder
        end
    end
```

## Network Security Groups (NSGs)

| NSG | Purpose | Key Rules |
|-----|---------|-----------|
| Frontend NSG | Secures web UI components | - Allow HTTPS inbound - Allow health probe |
| API NSG | Protects API services | - Allow internal subnet traffic - Block external access |
| Database NSG | Secures database access | - Allow API subnet access - Block external access |
| VM NSG | Controls VM access | - Allow maintenance access - Allow internal traffic |

## BC Gov Landing Zone Implementation

### Environment Structure

| Environment | Status | Description |
|-------------|--------|-------------|
| DEV | Planned | Development environment for building and testing new features |
| TEST | Deployed | Current deployment environment for testing and validation |
| PROD | Planned | Production environment for end-user access |
| TOOLS | Planned | Supporting tools and utilities for the application |

### Landing Zone Architecture

![BC Government Landing Zone Architecture](BCGovLandingZone.svg)

The application is built on the BC Government Landing Zone architecture, which provides a standardized approach to deploying applications in the Azure cloud environment.

For more details, see the [BC Gov Landing Zone Documentation](https://developer.gov.bc.ca/docs/default/component/public-cloud-techdocs/azure/get-started-with-azure/bc-govs-azure-landing-zone-overview/)

## Security & Compliance

- All internal services use Private Endpoints
- Network isolation through subnet segregation
- NSG rules following least-privilege access
- Compliance with BC Government security standards

## LLM Service Deployment Options

The system requires an LLM service and supports two deployment configurations:

### OLLAMA Deployment

| Component | Resource Type | Configuration |
|-----------|---------------|---------------|
| OLLAMA Service | Azure VM | Self-hosted model serving with configurable models |
| Network | VM Subnet + Private Endpoint | Secured access within VNet |
| Model Storage | VM Local Storage | Downloaded models cached locally |
| Configuration | Environment Variables | `MODEL_NAME`, `MODEL_VERSION` |

### Azure OpenAI Deployment

| Component | Resource Type | Configuration |
|-----------|---------------|---------------|
| Azure OpenAI | Azure OpenAI Service | Managed service with GPT models |
| Network | Private Endpoint | Secured access within VNet |
| Model Access | Azure Managed | GPT-3.5-turbo, GPT-4, or other available models |
| Configuration | Environment Variables | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY` |

**Deployment Selection**: Set `LLM_PROVIDER=ollama` or `LLM_PROVIDER=azure_openai` to choose deployment type.

**Note**: Both options provide the same API interface to the Web API component, ensuring consistent application behavior regardless of the chosen LLM provider.

## Azure Implementation Architecture

### Detailed Component Diagram

```mermaid
graph TB
    %% Nodes
    WebUI["Web UI<br>(React App)<br>VITE/NGINX<br>Azure App Service"]
    WebAPI["Web API<br>Python Flask Orchestrator<br>Private Endpoint Only<br>Azure App Service"]
    VectorAPI["Vector API<br>Python Flask Query Engine<br>Private Endpoint<br>Azure App Service"]
    VectorDB["Vector Database<br>Azure PostgreSQL Flexible Server<br>Private Endpoint"]
    LLM["LLM Service<br>OLLAMA or Azure OpenAI<br>VM or Azure Service<br>Private Endpoint"]
    Embedder["Document Embedder<br>Python Processor<br>VM<br>Manual Trigger"]
    Client["Client Browser"]
    
    %% NSG nodes
    FNSG["Frontend NSG"]
    ANSG["API NSG"]
    DNSG["Database NSG"]
    VNSG["VM NSG"]
    
    %% Connections
    Client -->|HTTPS| WebUI
    WebUI -->|NGINX Reverse Proxy<br>to Private Endpoint| WebAPI
    WebAPI -->|Private Endpoint| VectorAPI
    VectorAPI -->|Private Endpoint| VectorDB
    WebAPI -->|Private Endpoint| LLM
    Embedder -->|Populates| VectorDB
    
    %% NSG connections - visual relationship
    FNSG -.->|Secures| FSNET
    ANSG -.->|Secures| ASNET
    DNSG -.->|Secures| DSNET
    VNSG -.->|Secures| VSNET
    
    %% Azure Virtual Network Structure
    subgraph VNET["Azure Virtual Network"]
        subgraph FSNET["Frontend Subnet"]
            WebUI
        end
        subgraph ASNET["API Subnet"]
            WebAPI
            VectorAPI
        end
        subgraph DSNET["Database Subnet"]
            VectorDB
        end
        subgraph VSNET["VM Subnet"]
            LLM
            Embedder
        end
    end

    %% Styling
    %% Azure Services - Cool Blues
    style WebUI fill:#E3F2FD,color:#1565C0,stroke:#90CAF9,stroke-width:2px
    style WebAPI fill:#E3F2FD,color:#1565C0,stroke:#90CAF9,stroke-width:2px
    style VectorAPI fill:#E3F2FD,color:#1565C0,stroke:#90CAF9,stroke-width:2px
    style VectorDB fill:#E3F2FD,color:#1565C0,stroke:#90CAF9,stroke-width:2px
    style LLM fill:#E3F2FD,color:#1565C0,stroke:#90CAF9,stroke-width:2px
    style Embedder fill:#E3F2FD,color:#1565C0,stroke:#90CAF9,stroke-width:2px

    %% Client - Sage Green
    style Client fill:#E8F5E9,color:#2E7D32,stroke:#81C784,stroke-width:2px

    %% NSGs - Warm Orange for Security
    style FNSG fill:#FFF3E0,color:#E65100,stroke:#FFB74D,stroke-width:2px
    style ANSG fill:#FFF3E0,color:#E65100,stroke:#FFB74D,stroke-width:2px
    style DNSG fill:#FFF3E0,color:#E65100,stroke:#FFB74D,stroke-width:2px
    style VNSG fill:#FFF3E0,color:#E65100,stroke:#FFB74D,stroke-width:2px
    
    %% Network containers - Subtle Grey
    style VNET fill:none,stroke:#9E9E9E,stroke-width:2px
    style FSNET fill:none,stroke:#BDBDBD,stroke-width:1px,stroke-dasharray:5 5
    style ASNET fill:none,stroke:#BDBDBD,stroke-width:1px,stroke-dasharray:5 5
    style DSNET fill:none,stroke:#BDBDBD,stroke-width:1px,stroke-dasharray:5 5
    style VSNET fill:none,stroke:#BDBDBD,stroke-width:1px,stroke-dasharray:5 5
```
