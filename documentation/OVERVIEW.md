# EPIC.search Overview

EPIC.search is a document search and retrieval system that leverages AI technologies to provide intelligent document search capabilities.

## Key Features

- Semantic search using vector embeddings
- Keyword-based search capabilities
- AI-powered response generation
- Document processing and indexing
- Secure deployment within BC Government infrastructure

## Core Components

The system consists of several key components that work together to provide document search and retrieval capabilities:

- **Web Interface**: User-facing application for query input and results display
- **Search Orchestrator**: Coordinates search operations and AI response generation
- **Search Engine**: Handles vector and keyword-based search operations
- **Document Store**: Vector database storing document embeddings and metadata
- **AI Model**: Generates natural language responses from search results
- **Document Embedder**: Processes source documents and generates vector embeddings
- **Authentication**: Keycloak OIDC integration (planned)

```mermaid
graph TB
    Client[["User Browser"]]
    WebUI(["Web Interface"])
    Auth("Keycloak OIDC*")
    WebAPI["Search Orchestrator"]
    VectorAPI["Search Engine"]
    LLM{{"AI Model"}}
    VectorDB[("Vector Store")]
    Embedder["Document Embedder"]
    S3[("BC Gov S3")]
    
    Client -->|&nbsp;&nbsp;Query&nbsp;&nbsp;| WebUI
    WebUI -->|&nbsp;&nbsp;Auth Request&nbsp;&nbsp;| Auth
    Auth -->|&nbsp;&nbsp;Token&nbsp;&nbsp;| WebUI
    WebUI -->|&nbsp;&nbsp;Request + Token&nbsp;&nbsp;| WebAPI
    WebAPI -->|&nbsp;&nbsp;1. Search&nbsp;&nbsp;| VectorAPI
    VectorAPI -->|&nbsp;&nbsp;2. Documents&nbsp;&nbsp;| WebAPI
    WebAPI -->|&nbsp;&nbsp;3. Summarize&nbsp;&nbsp;| LLM
    LLM -->|&nbsp;&nbsp;4. Response&nbsp;&nbsp;| WebAPI
    VectorAPI -->|&nbsp;&nbsp;Query&nbsp;&nbsp;| VectorDB
    S3 -->|&nbsp;&nbsp;Source Docs&nbsp;&nbsp;| Embedder
    Embedder -->|&nbsp;&nbsp;Index&nbsp;&nbsp;| VectorDB

    %% Style Definitions
    classDef browser fill:#E3F2FD,stroke:#90CAF9,stroke-width:2px     %% Light Blue
    classDef ui fill:#E8EAF6,stroke:#9FA8DA,stroke-width:2px          %% Light Indigo
    classDef database fill:#E0F2F1,stroke:#80CBC4,stroke-width:2px    %% Light Teal
    classDef ai fill:#FCE4EC,stroke:#F48FB1,stroke-width:2px          %% Light Pink
    classDef api fill:#ECEFF1,stroke:#90A4AE,stroke-width:2px         %% Light Blue Grey
    classDef auth fill:#F3E5F5,stroke:#CE93D8,stroke-width:2px        %% Light Purple
    classDef embedder fill:#E0F7FA,stroke:#80DEEA,stroke-width:2px    %% Light Cyan
    
    %% Class Assignments
    class Client browser
    class WebUI ui
    class WebAPI,VectorAPI api
    class VectorDB,S3 database
    class LLM ai
    class Auth auth
    class Embedder embedder
```

**Note:** * Authentication not yet implemented

## Documentation Structure

Detailed documentation is split into two main areas:

### [Application Architecture](ARCHITECTURE.md)

- Component interactions and data flow
- AI models and configurations
- Search and retrieval processes
- Document processing pipeline

### [Infrastructure & Deployment](INFRASTRUCTURE.md)

- Azure implementation details
- Network architecture and security
- BC Gov Landing Zone integration
- Environment configurations

## Current Status

EPIC.search is deployed in the BC Gov Landing Zone **Test** environment. For detailed deployment information, see the [Infrastructure Documentation](INFRASTRUCTURE.md).

## Getting Started

- For developers: See [Application Architecture](ARCHITECTURE.md)
- For deployment: See [Infrastructure & Deployment](INFRASTRUCTURE.md)
- For API documentation: See [API Documentation](API.md)
