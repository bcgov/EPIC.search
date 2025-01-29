# EPIC.search - Embedder

The Embedder will convert the PDF file contents into a vector database


## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`EAO_SEARCH_API_BASE_URI`

`AWS_ENDPOINT_URI`

`AWS_BUCKET_NAME`

`AWS_ACCESS_KEY_ID`

`AWS_SECRET_ACCESS_KEY`

`AWS_REGION`

`VECTOR_DB_URL`

`POSTGRES_LOG_DATABASE_URL`

`INDEX_TABLE_NAME`

`CHUNK_DUMP_TABLE_NAME`

## Deployment

To run  this project follow the steps

Step 1 - Run Database docker command in .database folder

```bash
  docker compose up
```

Step 2 - Install the dependencies 
```bash
pip install -r requirements.txt
```

Step 3 - Run the embedder to add documents to the vector database

```bash
  python main.py
```




