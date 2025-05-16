# Application Architecture

## Overview

EPIC.search is a document search and retrieval system using modern AI techniques including vector search and Large Language Models (LLMs).

## Components Diagram

```mermaid
graph TB
    %% Core Application Components
    WebUI["Web UI\n(React App)"]
    WebAPI["Web API\nPython Flask Orchestrator"]
    VectorAPI["Vector API\nPython Flask Query Engine"]
    VectorDB["Vector Database\nPostgreSQL"]
    LLM["LLM Model\n(qwen2.5:0.5b)"]
    Embedder["Document Embedder\nPython Processor"]
    Client["Client Browser"]
    
    %% Core Application Flow
    Client -->|HTTPS| WebUI
    WebUI --> WebAPI
    WebAPI --> VectorAPI
    VectorAPI --> VectorDB
    WebAPI --> LLM
    Embedder -->|Populates| VectorDB
```

## Component Descriptions

- **Web UI**: React-based front-end application providing user interface
- **Web API**: Flask-based orchestration layer managing request flow
- **Vector API**: Specialized search engine handling vector and keyword searches
- **Vector Database**: PostgreSQL database storing document vectors and metadata
- **LLM Model**: AI model providing natural language understanding
- **Document Embedder**: Processing service converting documents to vectors

## Application Flow

```mermaid
sequenceDiagram
    participant Client as Client
    participant WebUI as Web UI
    participant WebAPI as Web API
    participant VectorAPI as Vector API
    participant VectorDB as Vector DB
    participant LLM as LLM Model
    
    Client->>WebUI: User query
    WebUI->>WebAPI: Forward query
    WebAPI->>VectorAPI: Process query
    VectorAPI->>VectorDB: Keyword search
    VectorDB-->>VectorAPI: Search results
    VectorAPI->>VectorDB: Semantic search
    VectorDB-->>VectorAPI: Search results
    VectorAPI->>VectorAPI: Rank & combine results
    VectorAPI-->>WebAPI: Return ranked results
    WebAPI->>LLM: Generate response
    LLM-->>WebAPI: RAG response
    WebAPI-->>WebUI: Return response
    WebUI-->>Client: Display to user
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
| OLLAMA | `qwen2.5:0.5b` | Lightweight LLM for text generation and RAG responses |
