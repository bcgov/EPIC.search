# EPIC.search - Embedder

The Embedder will convert the PDF file contents into a vector database.

## Environment Variables

To run this project, you will need to add the following environment variables to your `.env` file:

- `EAO_SEARCH_API_BASE_URI`
- `AWS_ENDPOINT_URI`
- `AWS_BUCKET_NAME`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `VECTOR_DB_URL`
- `POSTGRES_LOG_DATABASE_URL`
- `INDEX_TABLE_NAME`
- `CHUNK_DUMP_TABLE_NAME`

## Deployment

To run this project, follow these steps:

### Step 1: Start the Database

Run the following command in the `.database` folder to start the database using Docker:

```bash
docker compose up
```

### Step 2: Install Dependencies

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

### Step 3: Run the Embedder

#### Run as a Python Application

Run the embedder directly as a Python application by providing the `--project_id` argument:

```bash
python main.py --project_id <project_id>
```

If no `--project_id` is provided, the application will exit with a message:

```bash
No project_id provided. Exiting.
```

#### Run as a Docker Container

Build and run the Docker container, passing the `--project_id` argument during startup:

```bash
docker build -t embedder .
docker run --rm embedder --project_id <project_id>
```

## Notes

- The application no longer includes a Flask API. All functionality is accessed via the command-line interface or Docker container arguments.
- Logs and output will be printed to the console during execution.
