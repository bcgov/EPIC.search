# EPIC.search Data Flow Documentation

## Data Source and Public Access

> **Note**: All data processed by EPIC.search originates from publicly available sources, though access methods are secured:
> - BC EPIC (Environmental Assessment Office) public API
> - S3 storage containing publicly available EPIC documents (accessed via secure credentials)
> - While all document content is public, access to storage systems is properly secured
> - No private or restricted data is used in this system


## System Data Flow Overview

```mermaid
flowchart TB
    subgraph Public ["Public Data Sources"]
        EPIC["EPIC Public API"]
        S3["Public S3 Storage"]
    end

    subgraph Processing ["Data Processing"]
        Embedder["Document Embedder"]
        VectorDB["Vector Database<br>(PostgreSQL/pgvector)"]
    end

    subgraph Query ["Query Processing"]
        UI["Web UI"]
        SearchAPI["Search API<br>(Orchestrator)"]
        VectorAPI["Vector API"]
        LLM["LLM Service<br>(OLLAMA)"]
    end

    %% Data Ingestion Flow
    EPIC -->|"1. Project List"| Embedder
    S3 -->|"2. Document Download"| Embedder
    Embedder -->|"3. Process & Embed"| VectorDB

    %% Query Flow
    UI -->|"1. User Query"| SearchAPI
    SearchAPI -->|"2. Search Request"| VectorAPI
    VectorAPI -->|"3. Vector Query"| VectorDB
    VectorDB -->|"4. Results"| VectorAPI
    VectorAPI -->|"5. Ranked Results"| SearchAPI
    SearchAPI -->|"6. Context"| LLM
    LLM -->|"7. Response"| SearchAPI
    SearchAPI -->|"8. Final Result"| UI

    %% Styling
    classDef public fill:#2874A6,stroke:#2E86C1
    classDef process fill:#1E8449,stroke:#229954
    classDef query fill:#B03A2E,stroke:#C0392B
    
    class EPIC,S3 public
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
| Response Generation | OLLAMA (LLM) | Generates natural language responses using retrieved contexts |
| Result Delivery | Web UI | Formatted results displayed to user |

## Component Data Interactions

| Source Component | Target Component | Data Type | Flow Description |
|-----------------|------------------|------------|------------------|
| EPIC Public API | Document Embedder | Project & Document Metadata | List of projects and associated documents |
| S3 Storage | Document Embedder | Raw Documents | Secure access to public documents via authenticated connection |
| Document Embedder | Vector Database | Embeddings, Text & Metadata | Processed document vectors, corresponding text chunks, and metadata |
| Web UI | Search API | User Queries | Search requests and parameters |
| Search API | Vector API | Search Parameters | Query processing instructions |
| Vector API | Vector Database | Query & Results | Database queries and document retrieval |
| Vector API | Search API | Search Results | Ranked and filtered results |
| Search API | LLM | Context & Query | Document context for response generation |
| Search API | Web UI | Final Response | Formatted results for user display |

## Data Retention and Privacy

- All processed data originates from public sources
- No private information is stored or processed
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
| Response Generation | LLM processing time | Lightweight model selection (qwen2.5:0.5b) |
| Result Delivery | Response size | Pagination and result limiting |

> **Note**: The document embedding process is currently manually triggered. This allows for controlled updates and system maintenance windows. Future automation of this process is planned.
