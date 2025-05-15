# Architecture

## Flow

```mermaid
sequenceDiagram    box "Frontend Subnet (NSG)" 
    participant WebUI as Web UI<br/>(REACT App)<br/>VITE/NGINX<br/>Azure App Service
    end
    box "API Subnet (NSG)"
    participant WebAPI as Web API<br/>Orchestrator<br/>Private Endpoint<br/>NGINX Reverse Proxy Only<br/>Azure App Service
    participant VectorAPI as Vector API<br/>Query Engine<br/>Private Endpoint<br/>Azure App Service
    end
    box "Database Subnet (NSG)"
    participant VectorDB as Vector DB<br/>Hosted PostgreSQL<br/>Private Endpoint
    end
    box "VM Subnet (NSG)"
    participant LLM as LLM Model<br/>OLLAMA<br/>VM<br/>Private Endpoint
    end

    Note over WebUI,LLM: All components reside within the same VNET

    WebUI->>WebAPI: User captures a question<br/>(Reverse Proxy)
    WebAPI->>VectorAPI: Forward question<br/>(Private Endpoint)
    VectorAPI->>VectorDB: Perform keyword search<br/>(Private Endpoint)
    VectorDB-->>VectorAPI: Return keyword search results
    VectorAPI->>VectorDB: Perform semantic search<br/>(Private Endpoint)
    VectorDB-->>VectorAPI: Return semantic search results
    VectorAPI->>VectorAPI: Combine and rank results
    VectorAPI-->>WebAPI: Return ranked results<br/>(Private Endpoint)
    WebAPI->>LLM: Send query + response<br/>(Private Endpoint)
    LLM-->>WebAPI: Return result
    WebAPI-->>WebUI: Return result to user
```

## AI Models Configuration

### Vector API Models

| Purpose | Model Name | Description |
|---------|------------|-------------|
| Cross Encoder | `cross-encoder/ms-marco-MiniLM-L-2-v2` | Used for re-ranking search results |
| Embeddings | `all-mpnet-base-v2` | Used for generating vector embeddings |
| Keyword Processing | `all-mpnet-base-v2` | Used for keyword extraction and processing |

### LLM Configuration

| Service | Model | Description |
|---------|-------|-------------|
| OLLAMA | `qwen2.5:3b` | Lightweight LLM for text generation and RAG responses |

## Components Diagram

```mermaid
graph TB
    %% Nodes
    WebUI["Web UI<br>(React App)<br>VITE/NGINX<br>Azure App Service"]
    WebAPI["Web API<br>Orchestrator<br>Private Endpoint<br>Azure App Service"]
    VectorAPI["Vector API<br>Query Engine<br>Private Endpoint<br>Azure App Service"]
    VectorDB["Vector Database<br>PostgreSQL<br>Private Endpoint"]
    LLM["LLM Model<br>OLLAMA (qwen2.5:3b)<br>VM<br>Private Endpoint"]
    Client["Client Browser"]
    
    %% Connections
    Client -->|HTTPS| WebUI
    WebUI -->|Reverse Proxy| WebAPI
    WebAPI -->|Private Endpoint| VectorAPI
    VectorAPI -->|Private Endpoint| VectorDB
    WebAPI -->|Private Endpoint| LLM
    
    %% Styling
    style WebUI fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style WebAPI fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style VectorAPI fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style VectorDB fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style LLM fill:#0072C6,color:white,stroke:#0072C6,stroke-width:2px
    style Client fill:#86B342,color:white,stroke:#86B342,stroke-width:2px
    
    %% Grouping with labels
    subgraph VNET["Azure Virtual Network"]
        subgraph FSNET["Frontend Subnet (NSG)"]
            WebUI
        end
        subgraph ASNET["API Subnet (NSG)"]
            WebAPI
            VectorAPI
        end
        subgraph DSNET["Database Subnet (NSG)"]
            VectorDB
        end
        subgraph VSNET["VM Subnet (NSG)"]
            LLM
        end
    end
    
    %% Style the subnets
    style VNET fill:none,stroke:#666,stroke-width:2px
    style FSNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
    style ASNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
    style DSNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
    style VSNET fill:none,stroke:#666,stroke-width:1px,stroke-dasharray:5 5
```
