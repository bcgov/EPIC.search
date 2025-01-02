import logging
import time
from typing import Any, List, Optional, Tuple, Union
from datetime import datetime

import pandas as pd
from app.config.settings import get_settings
import ollama
from timescale_vector import client
import psycopg2
from sentence_transformers import CrossEncoder
from app.services.keyword_extractor import get_keywords
from app.services.embedding import get_embedding
from transformers import pipeline
from app.services.tag_extractor import get_tags
class VectorStore:
    """A class for managing vector operations and database interactions."""

    def __init__(self):
        """Initialize the VectorStore with settings and Timescale Vector configurations."""
        self.settings = get_settings()
        self.embedding_model = self.settings.embedding_model
        self.vector_settings = self.settings.vector_store
        self.ner_pipeline = pipeline("ner", grouped_entities=True)
        # A dictionary to store vec_clients keyed by table name for dynamic usage
        self._vec_clients = {}
    def get_client_for_table(self, table_name: str, embedding_dimensions: Optional[int] = None) -> client.Sync:
        """
        Retrieve or create a vec_client instance for a given table name.

        Args:
            table_name: Name of the table.
            embedding_dimensions: Embedding dimensions for the table. If None, defaults from settings are used.

        Returns:
            A timescale_vector.client.Sync instance for the given table.
        """
        if table_name not in self._vec_clients:
            if embedding_dimensions is None:
                embedding_dimensions = self.vector_settings.embedding_dimensions

            # Create a new client for this table
            vec_client = client.Sync(
                self.settings.database.service_url,
                table_name,
                embedding_dimensions,
                time_partition_interval=self.vector_settings.time_partition_interval
            )
            self._vec_clients[table_name] = vec_client
        return self._vec_clients[table_name]
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.

        Args:
            text: The input text to generate an embedding for.

        Returns:
            A list of floats representing the embedding.
        """
        
        start_time = time.time()
        # embedding = ollama.embed(
        #         input=text,
        #         model=self.embedding_model.model_name,
        #     )
        embedding = get_embedding(text)

        elapsed_time = time.time() - start_time
        logging.info(f"Embedding generated in {elapsed_time:.3f} seconds")
        # return embedding.embeddings[0]
        return embedding

    def create_table(self, table_name: str, embedding_dimensions: Optional[int] = None) -> None:
        """
        Create a new table for storing embeddings dynamically.

        Args:
            table_name: Name of the table to create.
            embedding_dimensions: Number of embedding dimensions. If None, use default from settings.
        """
        vec_client = self.get_client_for_table(table_name, embedding_dimensions)
        vec_client.create_tables()
        logging.info(f"Table '{table_name}' created successfully.")

    def create_index(self, table_name: str) -> None:
        """
        Create the StreamingDiskANN index on a specified table to speed up similarity search.

        Args:
            table_name: Name of the table to index.
        """
        vec_client = self.get_client_for_table(table_name)
        vec_client.create_embedding_index(client.DiskAnnIndex())
        logging.info(f"Index created on table '{table_name}'.")

    def drop_index(self, table_name: str) -> None:
        """
        Drop the StreamingDiskANN index from the specified table.

        Args:
            table_name: Name of the table to drop index from.
        """
        vec_client = self.get_client_for_table(table_name)
        vec_client.drop_embedding_index()
        logging.info(f"Index dropped from table '{table_name}'.")

    def upsert(self, table_name: str, records: List[dict]) -> None:
        """
        Upsert records into the specified table.

        Args:
            table_name: Name of the table to upsert into.
            records: A list of records (dicts) with embedding and metadata.
                     Each record typically includes 'embedding' and 'payload' keys.
        """
        vec_client = self.get_client_for_table(table_name)
        vec_client.upsert(records)
        logging.info(f"Upserted {len(records)} records into table '{table_name}'.")
    
    def delete_by_metadata(self, table_name: str, metadata_filters: dict) -> None:
        """
        Delete records from the specified table by metadata filters.

        Args:
            table_name: Name of the table from which records should be deleted.
            metadata_filters: A dictionary of metadata filters. Only records matching all filters are deleted.
        """
        vec_client = self.get_client_for_table(table_name)
        vec_client.delete_by_metadata(metadata_filters)
        logging.info(f"Deleted records from '{table_name}' matching metadata filters: {metadata_filters}.")
    
    def extract_metadata_from_question(self, question):
        """
        Dynamically extract metadata fields from a user question using the transformers NER model.
        """
        # Extract entities from the question
        entities = self.ner_pipeline(question)
        metadata_filter = {}

        # Process each detected entity dynamically
        for entity in entities:
            entity_text = entity["word"].strip()  # Extract the actual word
            entity_label = entity["entity_group"]  # Extract the group/category (e.g., DATE, ORG, etc.)

            # Dynamically assign metadata fields based on detected labels
            if "DATE" in entity_label:
                metadata_filter["year"] = entity_text
            elif "PERSON" in entity_label:
                metadata_filter["author"] = entity_text
            elif "ORG" in entity_label or "PRODUCT" in entity_label:
                metadata_filter["category"] = entity_text
            elif "GPE" in entity_label or "LOCATION" in entity_label:
                metadata_filter["location"] = entity_text
            else:
                # Handle generic text (if applicable)
                metadata_filter.setdefault("general", []).append(entity_text)

        # Simplify the general field to avoid lists unless necessary
        if "general" in metadata_filter and len(metadata_filter["general"]) == 1:
            metadata_filter["general"] = metadata_filter["general"][0]

        return metadata_filter
      

    def _create_dataframe_from_results(
        self,
        results: List[Tuple[Any, ...]],
    ) -> pd.DataFrame:
        """
        Create a pandas DataFrame from the search results.

        Args:
            results: A list of tuples containing the search results.

        Returns:
            A pandas DataFrame containing the formatted search results.
        """
        # Convert results to DataFrame
        df = pd.DataFrame(
            results, columns=["id", "metadata", "content", "embedding", "distance"]
        )

        # Expand metadata column
        # df = pd.concat(
        #     [df.drop(["metadata"], axis=1), df["metadata"].apply(pd.Series)], axis=1
        # )

        # Convert id to string for better readability
        df["id"] = df["id"].astype(str)

        return df

    def delete(
        self,
        ids: List[str] = None,
        metadata_filter: dict = None,
        delete_all: bool = False,
    ) -> None:
        """Delete records from the vector database.

        Args:
            ids (List[str], optional): A list of record IDs to delete.
            metadata_filter (dict, optional): A dictionary of metadata key-value pairs to filter records for deletion.
            delete_all (bool, optional): A boolean flag to delete all records.

        Raises:
            ValueError: If no deletion criteria are provided or if multiple criteria are provided.

        Examples:
            Delete by IDs:
                vector_store.delete(ids=["8ab544ae-766a-11ef-81cb-decf757b836d"])

            Delete by metadata filter:
                vector_store.delete(metadata_filter={"category": "Shipping"})

            Delete all records:
                vector_store.delete(delete_all=True)
        """
        if sum(bool(x) for x in (ids, metadata_filter, delete_all)) != 1:
            raise ValueError(
                "Provide exactly one of: ids, metadata_filter, or delete_all"
            )

        if delete_all:
            self.vec_client.delete_all()
            logging.info(f"Deleted all records from {self.vector_settings.table_name}")
        elif ids:
            self.vec_client.delete_by_ids(ids)
            logging.info(
                f"Deleted {len(ids)} records from {self.vector_settings.table_name}"
            )
        elif metadata_filter:
            self.vec_client.delete_by_metadata(metadata_filter)
            logging.info(
                f"Deleted records matching metadata filter from {self.vector_settings.table_name}"
            )

    def semantic_search(
        self,
        table_name : str,
        query: str,
        limit: int = 5,
        metadata_filter: Union[dict, List[dict]] = None,
        predicates: Optional[client.Predicates] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        return_dataframe: bool = True,
        ) -> Union[List[Tuple[Any, ...]], pd.DataFrame]:
        """
        Query the vector database for similar embeddings based on input text.

        More info:
            https://github.com/timescale/docs/blob/latest/ai/python-interface-for-pgvector-and-timescale-vector.md

        Args:
            query: The input text to search for.
            limit: The maximum number of results to return.
            metadata_filter: A dictionary or list of dictionaries for equality-based metadata filtering.
            predicates: A Predicates object for complex metadata filtering.
                - Predicates objects are defined by the name of the metadata key, an operator, and a value.
                - Operators: ==, !=, >, >=, <, <=
                - & is used to combine multiple predicates with AND operator.
                - | is used to combine multiple predicates with OR operator.
            time_range: A tuple of (start_date, end_date) to filter results by time.
            return_dataframe: Whether to return results as a DataFrame (default: True).

        Returns:
            Either a list of tuples or a pandas DataFrame containing the search results.
        """
        query_embedding = self.get_embedding(query)

        start_time = time.time()

        search_args = {
            "limit": limit,
        }
        metadata_filter = self.extract_metadata_from_question(query)
        tags = get_tags(query)  
        if tags:
            tags_filter = [{"tags": [tag]} for tag in tags]
            search_args["filter"] = tags_filter
        #if metadata_filter:
            # search_args["filter"] = metadata_filter

        if predicates:
            search_args["predicates"] = predicates

        if time_range:
            start_date, end_date = time_range
            search_args["uuid_time_filter"] = client.UUIDTimeRange(start_date, end_date)
        vec_client = self.get_client_for_table(table_name)
        results = vec_client.search(query_embedding[0], **search_args)
        elapsed_time = time.time() - start_time

        self._log_search_time("Vector", elapsed_time)

        if return_dataframe:
            return self._create_dataframe_from_results(results)
        else:
            return results
        

    def keyword_search(
        self,  table_name : str, query: str, limit: int = 5, return_dataframe: bool = True
    ) -> Union[List[Tuple[str, str, float]], pd.DataFrame]:
        """
        Perform a keyword search on the contents of the vector store.

        Args:
            query: The search query string.
            limit: The maximum number of results to return. Defaults to 5.
            return_dataframe: Whether to return results as a DataFrame. Defaults to True.

        Returns:
            Either a list of tuples (id, contents, rank) or a pandas DataFrame containing the search results.

        Example:
            results = vector_store.keyword_search("shipping options")
        """

        weighted_keywords = get_keywords(query)
        tags = get_tags(query)
        keywords = [keyword for keyword, weight in weighted_keywords]
        tsquery_str = " OR ".join(keywords)
        modified = f'"{tsquery_str}"'
        tags_condition = "metadata->'tags' ?| %s" if tags else "TRUE"
        search_sql = f"""
        SELECT id, contents, metadata, ts_rank_cd(to_tsvector('simple', contents), query) as rank
        FROM {table_name}, websearch_to_tsquery('simple', %s) query
        WHERE to_tsvector('simple', contents) @@ query  AND {tags_condition}
        ORDER BY rank DESC
        LIMIT %s
        """
     

        start_time = time.time()

        # Create a new connection using psycopg3
        with psycopg2.connect(self.settings.database.service_url) as conn:
            with conn.cursor() as cur:
                if tags:
                    cur.execute(search_sql, (tsquery_str, tags, limit))
                else:
                     cur.execute(search_sql, (tsquery_str, limit))
                results = cur.fetchall()

        elapsed_time = time.time() - start_time
        self._log_search_time("Keyword", elapsed_time)

        if return_dataframe:
            df = pd.DataFrame(results, columns=["id", "content", "metadata", "rank"])
            df["id"] = df["id"].astype(str)
            return df
        else:
            return results
    def _log_search_time(self, search_type: str, elapsed_time: float) -> None:
        """
        Log the time taken for a search operation.

        Args:
            search_type: The type of search performed (e.g., 'Vector', 'Keyword').
            elapsed_time: The time taken for the search operation in seconds.
        """
        logging.info(f"{search_type} search completed in {elapsed_time:.3f} seconds")

    

    def hybrid_search(
        self,
        table_name : str,
        query: str,
        keyword_k: int = 5,
        semantic_k: int = 5,
        rerank: bool = False,
        top_n: int = 5,
    ) -> pd.DataFrame:
        """
        Perform a hybrid search combining keyword and semantic search results,
        with optional reranking using Cohere.

        Args:
            query: The search query string.
            keyword_k: The number of results to return from keyword search. Defaults to 5.
            semantic_k: The number of results to return from semantic search. Defaults to 5.
            rerank: Whether to apply Cohere reranking. Defaults to True.
            top_n: The number of top results to return after reranking. Defaults to 5.

        Returns:
            A pandas DataFrame containing the combined search results with a 'search_type' column.

        Example:
            results = vector_store.hybrid_search("shipping options", keyword_k=3, semantic_k=3, rerank=True, top_n=5)
        """
        # Perform keyword search
        keyword_results = self.keyword_search(
           table_name, query, limit=keyword_k, return_dataframe=True
        )
        keyword_results["search_type"] = "keyword"
        keyword_results = keyword_results[["id", "content", "search_type", "metadata"]]

        # Perform semantic search
        semantic_results = self.semantic_search(
            table_name, query, limit=semantic_k, return_dataframe=True
        )
        semantic_results["search_type"] = "semantic"
        semantic_results = semantic_results[["id", "content", "search_type", "metadata"]]

        # Combine results
        combined_results = pd.concat(
            [keyword_results, semantic_results], ignore_index=True
        )

        # Remove duplicates, keeping the first occurrence (which maintains the original order)
        combined_results = combined_results.drop_duplicates(subset=["id"], keep="first")

        if rerank:
            return self._rerank_results(query, combined_results, top_n)

        return combined_results

    def _rerank_results(
        self, query: str, combined_results: pd.DataFrame, top_n: int
    ) -> pd.DataFrame:
        """
        Rerank the combined search results using Cohere.

        Args:
            query: The original search query.
            combined_results: DataFrame containing the combined keyword and semantic search results.
            top_n: The number of top results to return after reranking.

        Returns:
            A pandas DataFrame containing the reranked results.
        """
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        documents=combined_results["content"].tolist()
            # Map topk to [compared_text, doc_field] pairs list
        pairs = [[query, doc] for doc in documents]
            # Produces list of float values. Higher is more closely related. Should be parallel with pairs list.
        scores = model.predict(pairs)
       
        reranked_df = pd.DataFrame(
            [
                {
                    "id": result["id"],
                    "content": result["content"],
                    "search_type": result["search_type"],
                    "relevance_score": scores[i],
                    "metadata": result["metadata"],
                }
               for i, (_, result) in enumerate(combined_results.iterrows())
            ]
        )

        sorted_df = reranked_df.sort_values("relevance_score", ascending=False)
        top_n_records = sorted_df.head(top_n)
        return top_n_records