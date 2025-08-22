# EPIC.search Embedder Scripts

This directory contains utility scripts for maintenance and updates to the EPIC.search Embedder system.

## Available Scripts

### update_keywords_retrospectively.py

This script retrospectively updates keywords for successfully embedded documents using a configurable keyword extraction mode. It excludes documents that used Azure Vision service as they have custom keywords.

**Features:**

- Connects to the database and finds all successful documents
- Excludes documents that used Azure Vision service (custom keywords)
- Re-extracts keywords for document chunks using the specified mode
- Updates chunk metadata with new keywords
- Consolidates document keywords into a unique list
- Regenerates document-level embeddings (from tags, keywords, headings)

**Usage:**

```bash
# Update all documents with the mode from .env
python scripts/update_keywords_retrospectively.py

# Use specific keyword extraction mode
python scripts/update_keywords_retrospectively.py --mode fast

# Process only a specific project
python scripts/update_keywords_retrospectively.py --project_id 681a6e4e85cefd0022839a0e

# Dry run to see what would be changed
python scripts/update_keywords_retrospectively.py --dry_run

# Limit processing for testing
python scripts/update_keywords_retrospectively.py --limit 10

# Combine options
python scripts/update_keywords_retrospectively.py --mode standard --project_id 681a6e4e85cefd0022839a0e --dry_run
```

**Keyword Extraction Modes:**

- `standard`: Full KeyBERT quality (baseline, slowest)
- `fast`: KeyBERT optimized + batch processing (2-4x faster, query-compatible)
- `simplified`: TF-IDF ultra-fast (10-50x faster, may affect search quality)

### update_metadata_s3keys.py

This script retrospectively updates the metadata in the chunks and tags tables to include S3 keys for all documents. It's designed to be run manually on a VM within the vnet.

#### Purpose

The script:

- Fetches all projects and their documents from the API
- Creates a mapping of document IDs to S3 keys
- Updates the metadata in both `document_chunks` and `document_tags` tables
- Processes records in batches to manage memory usage
- Provides progress tracking and error reporting

#### Prerequisites

- Access to the EPIC API
- Database connection credentials configured in environment variables
- Python environment with required dependencies installed

#### Running the Script

1. If using virtual environment (recommended):

   ```powershell
   cd c:\Repos\EPIC.search\tools\embedder
   cd .venv\Scripts
   .\activate
   cd ..\..
   ```

2. Ensure you are in the embedder root directory:

   ```powershell
   cd c:\Repos\EPIC.search\tools\embedder
   ```

3. Run the script:

   ```powershell
   python scripts/update_metadata_s3keys.py
   ```

Note: You'll see `(.venv)` in your terminal prompt when the virtual environment is active.

#### Features

- **Batch Processing**: Updates records in configurable batch sizes (default 1000)
- **Progress Tracking**: Shows percentage complete and records processed
- **Error Handling**: Tracks and reports any errors encountered
- **Safe to Rerun**: Only updates records that don't already have an s3_key
- **Transaction Support**: Commits changes after each batch

#### Output

The script provides detailed progress information:

```text
Starting metadata update at 2025-06-13 10:00:00
Found 50 total projects to process
Processing project: Project Name (project_id)
...
Processing table: document_chunks
Total records to process: 10000
Progress: 10.00% - Updated: 1000, Errors: 0
...
Table document_chunks completed in 0:05:30
Records updated: 9800
Errors encountered: 200
...
Script completed in 0:15:45
```

#### Troubleshooting

If the script is interrupted, you can safely run it again. It will only process records that haven't been updated yet.

Common issues:

- **API Connection**: Ensure you have network access to the EPIC API
- **Database Connection**: Verify your database connection settings
- **Memory Usage**: If memory usage is high, try reducing the batch size

#### Environment Variables

The script uses the same environment variables as the main embedder application:

- `DOCUMENT_SEARCH_URL`: API endpoint
- `VECTOR_DB_URL`: Vector database connection string
- All other standard embedder environment variables
