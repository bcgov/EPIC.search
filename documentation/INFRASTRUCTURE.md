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
    LLM["LLM Model\nOLLAMA\nVM"]
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

## Azure Implementation Architecture

### Detailed Component Diagram

```mermaid
graph TB
    %% Nodes
    WebUI["Web UI<br>(React App)<br>VITE/NGINX<br>Azure App Service"]
    WebAPI["Web API<br>Python Flask Orchestrator<br>Private Endpoint Only<br>Azure App Service"]
    VectorAPI["Vector API<br>Python Flask Query Engine<br>Private Endpoint<br>Azure App Service"]
    VectorDB["Vector Database<br>Azure PostgreSQL Flexible Server<br>Private Endpoint"]
    LLM["LLM Model<br>OLLAMA (qwen2.5:0.5b)<br>VM<br>Private Endpoint"]
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
    style WebUI fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style WebAPI fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style VectorAPI fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style VectorDB fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style LLM fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style Embedder fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style Client fill:#86B342,color:white,stroke:#86B342,stroke-width:2px
    style FNSG fill:#D83B01,color:white,stroke:#D83B01,stroke-width:2px
    style ANSG fill:#D83B01,color:white,stroke:#D83B01,stroke-width:2px
    style DNSG fill:#D83B01,color:white,stroke:#D83B01,stroke-width:2px
    style VNSG fill:#D83B01,color:white,stroke:#D83B01,stroke-width:2px
    
    style VNET fill:none,stroke:#666,stroke-width:2px
    style FSNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
    style ASNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
    style DSNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
    style VSNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
```

### Component Deployment Details

[Continue with existing infrastructure documentation...]