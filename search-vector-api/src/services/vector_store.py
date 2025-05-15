"""PostgreSQL vector database interface for semantic search operations.

This module provides a direct interface to PostgreSQL with pgvector extension,
enabling both semantic vector similarity search and keyword-based full-text search.
It handles the low-level database operations including:

1. Vector similarity matching using pgvector's cosine similarity operators (<=>)
2. Keyword-based search using PostgreSQL's full-text search capabilities
3. Result filtering by tags, metadata, and time ranges
4. Performance tracking of search operations

The VectorStore class is designed to be agnostic of the specific embedding models
or document structures, focusing purely on efficient database interaction.
"""

import logging
import time
import pandas as pd
import psycopg

from typing import Any, List, Optional, Tuple, Union
from datetime import datetime
from flask import current_app
from .bert_keyword_extractor import get_keywords
from .embedding import get_embedding
from .tag_extractor import get_tags

class VectorStore:
    """
    A service for vector-based and keyword-based document search using pgvector.
    
    This class provides methods for semantic vector search and keyword-based search
    on documents stored in a PostgreSQL database with the pgvector extension.
    """

    def __init__(self):
        """Initialize a VectorStore instance."""
        pass

    def _create_dataframe_from_results(
        self,
        results: List[Tuple[Any, ...]],
    ) -> pd.DataFrame:
        """
        Convert database query results into a pandas DataFrame.
        
        Args:
            results: A list of tuples returned from a database query.
            
        Returns:
            A pandas DataFrame with the search results.
        """
        df = pd.DataFrame(
            results, columns=["id", "metadata", "content", "embedding", "distance"]
        )
        df["id"] = df["id"].astype(str)
        return df

    def semantic_search(
        self,
        table_name: str,
        query: str,
        limit: int = 5,
        predicates: Optional[dict] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        return_dataframe: bool = True,
    ) -> Union[List[Tuple[Any, ...]], pd.DataFrame]:
        """
        Search for documents similar to the query vector using pgvector directly.
        
        This method performs a semantic search using vector similarity with pgvector,
        converting the query text into embeddings and finding the most similar documents.
        
        Args:
            table_name: The table to search in.
            query: The search query text.
            limit: Maximum number of results to return (default: 5).
            predicates: Optional dictionary of field-value pairs to filter results.
            time_range: Optional tuple of (start_date, end_date) to filter by creation time.
            return_dataframe: If True, returns results as a DataFrame; otherwise as a list of tuples.
            
        Returns:
            Either a pandas DataFrame or a list of tuples containing search results.
        """
        query_embedding = get_embedding([query])
        start_time = time.time()

        # Build the WHERE clause based on filters
        where_conditions = ["TRUE"]
        params = []
        
        # Handle tags filter
        tags = get_tags(query)
        if tags:
            where_conditions.append("metadata->'tags' ?| %s")
            params.append(tags)
        
        # Handle time range filter
        if time_range:
            start_date, end_date = time_range
            where_conditions.append("(metadata->>'created_at')::timestamp BETWEEN %s AND %s")
            params.append(start_date)
            params.append(end_date)
        
        # Handle predicates for additional filtering
        if predicates:
            for key, value in predicates.items():
                where_conditions.append(f"metadata->>{key} = %s")
                params.append(value)
        
        # Build the final WHERE clause
        where_clause = " AND ".join(where_conditions)
        
        # Convert numpy array to Python list for database
        embedding_list = query_embedding[0].tolist()
        
        # Construct the SQL query using cosine distance with pgvector
        search_sql = f"""
        SELECT id, metadata, content, embedding, 1 - (embedding <=> %s::vector) as similarity
        FROM {table_name}
        WHERE {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """
        
        # Add query embedding and limit to params
        params.append(embedding_list)
        params.append(embedding_list)
        params.append(limit)
        
        # Execute the query using psycopg
        conn_params = current_app.vector_settings.database_url
        with psycopg.connect(conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute(search_sql, params)
                results = cur.fetchall()
        
        elapsed_time = time.time() - start_time
        self._log_search_time("Vector", elapsed_time)
        
        if return_dataframe:
            return self._create_dataframe_from_results(results)
        else:
            return results

    def keyword_search(
        self, table_name: str, query: str, limit: int = 5, return_dataframe: bool = True
    ) -> Union[List[Tuple[str, str, float]], pd.DataFrame]:
        """
        Search for documents using keyword-based full-text search.
        
        This method uses PostgreSQL's full-text search capabilities to find documents
        that match the keywords extracted from the query.
        
        Args:
            table_name: The table to search in.
            query: The search query text.
            limit: Maximum number of results to return (default: 5).
            return_dataframe: If True, returns results as a DataFrame; otherwise as a list of tuples.
            
        Returns:
            Either a pandas DataFrame or a list of tuples containing search results.
        """
        weighted_keywords = get_keywords(query)
        tags = get_tags(query)
        keywords = [keyword for keyword, weight in weighted_keywords]
        tsquery_str = " OR ".join(keywords)
        modified = f'"{tsquery_str}"'
        tags_condition = "metadata->'tags' ?| %s" if tags else "TRUE"
        search_sql = f"""
        SELECT id, content, metadata, ts_rank_cd(to_tsvector('simple', content), query) as rank
        FROM {table_name}, websearch_to_tsquery('simple', %s) query
        WHERE to_tsvector('simple', content) @@ query  AND {tags_condition}
        ORDER BY rank DESC
        LIMIT %s
        """

        start_time = time.time()

        # Create a new connection using psycopg
        conn_params = current_app.vector_settings.database_url
        with psycopg.connect(conn_params) as conn:
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
            search_type: The type of search (e.g., "Vector", "Keyword").
            elapsed_time: The time taken for the search operation in seconds.
        """
        logging.info(f"{search_type} search completed in {elapsed_time:.3f} seconds")
