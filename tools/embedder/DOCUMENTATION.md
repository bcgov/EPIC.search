# EPIC.search Embedder - Technical Documentation

## System Architecture

The EPIC.search Embedder is a document processing system that converts PDF documents into vector embeddings stored in a database for semantic search capabilities. The system follows a modular architecture with the following key components:

### Core Components

1. **Main Processor (`main.py`)** - Entry point that handles project and document processing workflow
2. **Processor Service (`processor.py`)** - Manages batch processing of files with parallel execution
3. **Loader Service (`loader.py`)** - Handles document loading, text extraction, and vector embedding
4. **Logger Service (`logger.py`)** - Tracks document processing status in a database

### Data Flow

1. Document IDs are fetched from the API for a specific project
2. Document processing status is checked to avoid re-processing
3. Documents are processed in batches using parallel execution
4. Each document is:
   - Downloaded from S3
   - Converted from PDF to markdown
   - Chunked into smaller text segments
   - Embedded using a vector model
   - Stored in a vector database
   - Tagged and indexed for search

## NLP Model Architecture

The system uses two distinct models for different NLP tasks:

### 1. Document Embedding Model

```python
def get_embedding(texts):
    """
    Generate vector embeddings for one or more text inputs using the embedding model.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        model_name = settings.embedding_model_settings.model_name
        _model = SentenceTransformer(model_name)
    # ...
```

This model (configured via `EMBEDDING_MODEL_NAME`) is specifically used to generate vector embeddings for document chunks. These embeddings are stored in the vector database and used for semantic search queries. The model dimensions should match the `EMBEDDING_DIMENSIONS` setting.

### 2. Keyword Extraction Model

```python
def get_keywords(text):
    """
    Extract the most relevant keywords from the input text using the keyword model.
    """
    global _keymodel
    if _keymodel is None:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer
        
        model_name = settings.keyword_extraction_settings.model_name
        sentence_model = SentenceTransformer(model_name)
        _keymodel = KeyBERT(model=sentence_model)
    # ...
```

This model (configured via `KEYWORD_MODEL_NAME`) is used to extract relevant keywords from document chunks. These keywords are used to enhance search capabilities through tag-based filtering and relevance boosting.

### Model Independence

While both models default to using the same underlying transformer ('all-mpnet-base-v2'), they are implemented as separate instances with their own configuration, allowing for:

1. Task-specific optimization (different models can be used for each task)
2. Independent scaling (models can be loaded/unloaded based on resource constraints)
3. Future extensibility (specialized models can be integrated for each task)

### Lazy Loading Pattern

Both models implement a lazy loading pattern, initializing only when first used. This improves application startup time and reduces resource usage when a particular function is not needed.

## Key Components

### Project Processor (`process_projects`)

```python
def process_projects(project_id=None):
    """
    Process documents for one or all projects.
    
    This function:
    1. Initializes the database connections
    2. Fetches project information from the API
    3. For each project, retrieves its documents
    4. Filters out already processed documents
    5. Processes new documents in batches
    
    Args:
        project_id (str, optional): Process a specific project. If None, all projects are processed.
        
    Returns:
        dict: A dictionary containing the processing results
    """
```

The `process_projects` function is the main orchestrator of the document processing workflow. It can process either a single project (if `project_id` is provided) or all available projects. It manages pagination for both projects and files, avoiding re-processing of files that have already been processed.

### File Processor (`process_files`)

```python
def process_files(project_id, file_keys, metadata_list, batch_size=4):
    """
    Process a batch of files by loading and embedding their contents.
    
    This function processes files in batches using a ProcessPoolExecutor for parallel execution.
    For each file, it attempts to load and process the data, then logs the result.
    
    Args:
        project_id (str): The ID of the project these files belong to
        file_keys (list): List of file keys or paths to be processed
        metadata_list (list): List of metadata dictionaries corresponding to each file
        batch_size (int, optional): Number of files to process in parallel. Defaults to 4.
    """
```

The `process_files` function processes a batch of files in parallel using Python's `ProcessPoolExecutor`. It submits each file for processing and handles the results, logging whether the processing was successful or not.

### Document Loader (`load_data`)

```python
def load_data(s3_key, base_metadata):
    """
    Load and process a document from S3, embedding its content into the vector store.
    
    This function:
    1. Downloads the document from S3
    2. Converts PDF to markdown
    3. Splits markdown into chunks
    4. Creates embeddings for each chunk
    5. Stores chunks and embeddings in the vector store
    6. Extracts and stores tags from the document
    
    Args:
        s3_key (str): The S3 key of the file to process
        base_metadata (dict): Base metadata to attach to all chunks
    
    Returns:
        str: The S3 key of the processed file if successful
    """
```

The `load_data` function does the heavy lifting of document processing. It downloads a document from S3, extracts its text content, splits it into chunks, creates vector embeddings, and stores them in the vector database.

### Processing Logger (`log_processing_result`)

```python
def log_processing_result(project_id, document_id, status):
    """
    Log the result of processing a document to the database.
    
    Args:
        project_id (str): The ID of the project the document belongs to
        document_id (str): The ID of the document that was processed
        status (str): The status of the processing operation ('success' or 'failure')
    """
```

The `log_processing_result` function records the result of document processing in a database, which is later used to avoid re-processing documents that have already been processed.

## Docker Deployment

The Embedder can be deployed as a Docker container with options for optimizing startup time and performance. The system supports two different deployment strategies:

### Docker Build Options

#### 1. Standard Build (Runtime Model Loading)

In this approach, the Docker image is built without preloading any NLP models:

```bash
docker build -t epic-search-embedder .
```

With this build, the container will:

- Download required embedding models at runtime
- Use the environment variables to determine which models to download
- Experience a delay during the first processing run while models are downloaded

This approach is suitable for development environments or where container image size is a concern.

#### 2. Preloaded Models Build

In this approach, the specified NLP models are downloaded and cached during the Docker image build:

```bash
# Preload both models with different transformer models
docker build -t epic-search-embedder \
  --build-arg PRELOAD_EMBEDDING_MODEL="all-mpnet-base-v2" \
  --build-arg PRELOAD_KEYWORD_MODEL="distilbert-base-nli-stsb-mean-tokens" .
```

With this build, the container will:

- Include the pre-downloaded models directly in the image
- Start processing immediately without model download delay
- Have a larger image size due to the included model files

This approach is recommended for production environments where quick startup time is important.

### Model Preloading Mechanism

The `preload_models.py` script handles the downloading and initialization of required NLP models:

```python
def download_models():
    """
    Download and initialize NLP models required by the application.
    
    This function pre-downloads both the embedding model and keyword extraction model
    specified in the environment variables and initializes the KeyBERT model.
    """
    # Pre-download the embedding model
    embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")
    if embedding_model_name is None:
        print("ERROR: EMBEDDING_MODEL_NAME environment variable is required.")
        sys.exit(1)
        
    embedding_transformer = SentenceTransformer(embedding_model_name)
    
    # Pre-download the keyword extraction model
    keyword_model_name = os.getenv("KEYWORD_MODEL_NAME")
    if keyword_model_name is None:
        keyword_model_name = embedding_model_name
        keyword_transformer = embedding_transformer
    else:
        if keyword_model_name == embedding_model_name:
            keyword_transformer = embedding_transformer
        else:
            keyword_transformer = SentenceTransformer(keyword_model_name)
            
    # Initialize KeyBERT with the keyword model
    _ = KeyBERT(model=keyword_transformer)
```

This script is executed at build time when build arguments are provided, embedding the downloaded model files into the Docker image. It intelligently handles cases where both models are the same and reuses the instances for efficiency.

## Database Structure

The system uses two types of databases:

1. **PostgreSQL with pgvector** - Stores document chunks and their vector embeddings
   - `index_table` - Stores document tags with their embeddings
   - `chunk_table` - Stores document chunks with their embeddings

2. **PostgreSQL** - Stores processing logs
   - `processing_logs` - Records which documents have been processed and their status

## Configuration

The system is configured using environment variables, which are loaded by the `get_settings()` function in `src/config/settings.py`. Key configuration options include:

- API connection details
- S3 storage details
- Vector database connection
- Processing logs database connection
- Processing concurrency settings
- Model selection and configuration

### Environment Variables for Model Configuration

The model configuration uses two key environment variables:

| Variable Name | Purpose | Default Value |
|---------------|---------|---------------|
| EMBEDDING_MODEL_NAME | Model for generating document embeddings | "all-mpnet-base-v2" |
| KEYWORD_MODEL_NAME | Model for extracting keywords | "all-mpnet-base-v2" |

Each model can be configured independently to optimize for its specific task, or they can share the same model for simplicity.

## Error Handling

The system implements error handling at multiple levels:

1. Individual document processing errors are caught and logged
2. Processing continues even if individual documents fail
3. Multiprocessing cleanup ensures resources are properly released

### Known Issues

#### ProcessPoolExecutor Shutdown Error

When the application exits, you might occasionally see the following error in the logs:

```code
Exception ignored in: <function _ExecutorManagerThread.__init__.<locals>.weakref_cb at 0x000001691B6F1760>
Traceback (most recent call last):
  File "C:\Users\AndreGoncalves\AppData\Local\Programs\Python\Python312\Lib\concurrent\futures\process.py", line 310, in weakref_cb
AttributeError: 'NoneType' object has no attribute 'util'
```

This is a known issue related to Python's `concurrent.futures.ProcessPoolExecutor` module during interpreter shutdown. It occurs because during Python's shutdown sequence, some module globals are cleared before all weakref callbacks complete execution.

This error is harmless and doesn't affect program execution or results. The error has been suppressed in the application using the `suppress_process_pool_errors` utility function.

## Extensibility

The modular design allows for several extension points:

1. Support for different document types (beyond PDF)
2. Alternative vector embedding models
3. Different chunking strategies for various content types
4. Alternative storage backends for vectors
5. Specialized keyword extraction models for specific domains or languages
