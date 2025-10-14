# EPIC.search Data Flow Documentation

## Data Source and Public Access

> **Note**: All data processed by EPIC.search originates from publicly available sources, though storage and access methods are secured

- BC EPIC (Environmental Assessment Office) public API
- BC Government S3 storage containing copies of publicly available EPIC documents
- S3 storage is secured and requires authenticated access
- While documents are publicly available through BC websites, storage access is restricted
- All storage systems and APIs require proper authentication
- No private or restricted data is used in this system

## System Data Flow Overview

```mermaid
flowchart TB
    subgraph Public ["Data Sources"]
        EPIC["EPIC Public API"]
        direction TB
        subgraph Secure ["BC Gov Infrastructure"]
            S3[("Secure S3 Storage")]
        end
    end

    subgraph Processing ["Data Processing"]
        Embedder["Document Embedder"]
        VectorDB["Vector Database<br>(PostgreSQL/pgvector)"]
    end

    subgraph Query ["Query Processing"]
        UI["Web UI"]
        SearchAPI["Search API<br>(Orchestrator)"]
        VectorAPI["Vector API"]
        LLM["LLM Service<br>(OLLAMA or Azure OpenAI)"]
    end

    %% Data Ingestion Flow
    EPIC -->|Project List| Embedder
    S3 -->|Authenticated Access| Embedder
    Embedder -->|Process & Embed| VectorDB

    %% Query Flow
    UI -->|User Query| SearchAPI
    SearchAPI -->|Search Request| VectorAPI
    VectorAPI -->|Vector Query| VectorDB
    VectorDB -->|Results| VectorAPI
    VectorAPI -->|Ranked Results| SearchAPI
    SearchAPI -->|Context| LLM
    LLM -->|Response| SearchAPI
    SearchAPI -->|Final Result| UI

    %% Styling
    classDef public fill:#E3F2FD,stroke:#90CAF9,stroke-width:2px      %% Light Blue
    classDef secure fill:#E8F5E9,stroke:#81C784,stroke-width:2px      %% Light Green
    classDef process fill:#F3E5F5,stroke:#CE93D8,stroke-width:2px     %% Light Purple
    classDef query fill:#FFF3E0,stroke:#FFB74D,stroke-width:2px       %% Light Orange
    
    class EPIC public
    class S3 secure
    class Embedder,VectorDB process
    class UI,SearchAPI,VectorAPI,LLM query
```

## Document Processing Flow

```mermaid
sequenceDiagram
    participant EPIC as EPIC API
    participant S3 as S3 Storage
    participant Embedder as Document Embedder
    participant VectorDB as Vector Database

    Note over EPIC,VectorDB: Document Processing Pipeline
    
    Embedder->>EPIC: Query for project list
    EPIC-->>Embedder: Return project metadata
    loop For each project
        Embedder->>EPIC: Get document links
        EPIC-->>Embedder: Return document metadata
        loop For each document
            Embedder->>S3: Download document
            S3-->>Embedder: Return document content
            Note over Embedder: Local Processing:<br>1. Chunk document into segments<br>2. Generate vectors for each chunk<br>3. Extract metadata<br>4. Prepare text chunks for storage
            Embedder->>VectorDB: Store embeddings & metadata
            Note over Embedder: Delete local document
        end
    end
```

## User Query Flow

```mermaid
sequenceDiagram
    participant User as User Browser
    participant UI as Web UI
    participant SearchAPI as Search API
    participant VectorAPI as Vector API
    participant VectorDB as Vector DB
    participant LLM as LLM Model

    User->>UI: Submit search query
    UI->>SearchAPI: Forward query
    SearchAPI->>VectorAPI: Process query
    VectorAPI->>VectorDB: Perform keyword search
    VectorDB-->>VectorAPI: Return keyword results
    VectorAPI->>VectorDB: Perform semantic search
    VectorDB-->>VectorAPI: Return semantic results
    Note over VectorAPI: Combine & rank results
    VectorAPI-->>SearchAPI: Return ranked results
    SearchAPI->>LLM: Generate response with context
    LLM-->>SearchAPI: Return RAG response
    SearchAPI-->>UI: Return formatted response
    UI-->>User: Display results
```

## Data Flow Stages

### 1. Data Ingestion (Document Embedder)

| Stage | Process | Details |
|-------|---------|----------|
| Initial Data Discovery | EPIC API Query | Embedder queries BC EPIC public API to retrieve project listings and associated document metadata |
| Document Retrieval | S3 Download | Documents are temporarily downloaded from S3 storage using secure credentials (documents themselves are publicly available) |
| Document Processing | Local Processing | Documents are chunked into segments, vectorized, and embedded locally |
| Data Storage | Vector Database | Processed embeddings, text chunks, and metadata stored in PostgreSQL with pgvector |
| Cleanup | Local Cleanup | Temporary document copies are deleted after processing |

### 2. Data Query Flow (User Interaction)

| Stage | Component | Process |
|-------|-----------|----------|
| User Query | search-web (React) | User submits search query through web interface |
| Query Orchestration | search-api (Flask) | Orchestrates the search process and RAG implementation |
| Vector Search | search-vector-api (Flask) | Performs vector similarity search and keyword matching |
| Database Query | PostgreSQL/pgvector | Retrieves relevant document chunks based on search criteria |
| Response Generation | LLM Service (OLLAMA or Azure OpenAI) | Generates natural language responses using retrieved contexts |
| Result Delivery | Web UI | Formatted results displayed to user |

## Component Data Interactions

| Source Component | Target Component | Data Type | Flow Description |
|-----------------|------------------|------------|------------------|
| EPIC Public API | Document Embedder | Project & Document Metadata | List of projects and associated documents |
| S3 Storage | Document Embedder | Raw Documents | Access to document copies via authenticated BC Government S3 connection |
| Document Embedder | Vector Database | Embeddings, Text & Metadata | Processed document vectors, corresponding text chunks, and metadata |
| Web UI | Search API | User Queries | Search requests and parameters |
| Search API | Vector API | Search Parameters | Query processing instructions |
| Vector API | Vector Database | Query & Results | Database queries and document retrieval |
| Vector API | Search API | Search Results | Ranked and filtered results |
| Search API | LLM | Context & Query | Document context for response generation |
| Search API | Web UI | Final Response | Formatted results for user display |

## Data Retention and Privacy

- All processed data originates from public sources
- Documents are stored securely in BC Government infrastructure
- Access to storage systems requires proper authentication
- Document source links reference back to public EPIC system
- Vector database contains only:
  - Document embeddings (vector representations)
  - Associated text chunks (the actual document segments)
  - Public metadata
  - Source reference information

## Performance Considerations

| Stage | Consideration | Mitigation |
|-------|--------------|------------|
| Document Processing | Large file downloads | Temporary storage with immediate cleanup |
| Vector Search | Query performance | Optimized index and batch parameters |
| Response Generation | LLM processing time | Lightweight model selection (OLLAMA: qwen2.5:0.5b) or managed service (Azure OpenAI: GPT-3.5-turbo) |
| Result Delivery | Response size | Pagination and result limiting |

> **Note**: The document embedding process is currently manually triggered. This allows for controlled updates and system maintenance windows. Future automation of this process is planned.
