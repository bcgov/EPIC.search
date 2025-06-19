# EPIC.search Embedder Scripts

This directory contains utility scripts for maintenance and updates to the EPIC.search Embedder system.

## Available Scripts

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
