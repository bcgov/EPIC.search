import logging
import time
from typing import Any, List, Optional, Tuple, Union
from datetime import datetime
from flask import current_app
import pandas as pd
from timescale_vector import client
import psycopg2
from .bert_keyword_extractor import get_keywords
from .embedding import get_embedding
from .tag_extractor import get_tags


class VectorStore:

    def __init__(self):
        self._vec_clients = {}

    def get_client_for_table(
        self, table_name: str, embedding_dimensions: Optional[int] = None
    ) -> client.Sync:
        if table_name not in self._vec_clients:
            if embedding_dimensions is None:
                embedding_dimensions = current_app.config["EMBEDDING_DIMENSIONS"]

            # Create a new client for this table
            vec_client = client.Sync(
                current_app.config["VECTOR_DB_URL"],
                table_name,
                embedding_dimensions,
                time_partition_interval=current_app.config["TIME_PARTITION_INTERVAL"],
            )
            self._vec_clients[table_name] = vec_client
        return self._vec_clients[table_name]

    def _create_dataframe_from_results(
        self,
        results: List[Tuple[Any, ...]],
    ) -> pd.DataFrame:

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
        predicates: Optional[client.Predicates] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        return_dataframe: bool = True,
    ) -> Union[List[Tuple[Any, ...]], pd.DataFrame]:

        query_embedding = get_embedding([query])

        start_time = time.time()

        search_args = {
            "limit": limit,
        }

        tags = get_tags(query)
        if tags:
            tags_filter = [{"tags": [tag]} for tag in tags]
            search_args["filter"] = tags_filter

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
        self, table_name: str, query: str, limit: int = 5, return_dataframe: bool = True
    ) -> Union[List[Tuple[str, str, float]], pd.DataFrame]:
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
        with psycopg2.connect(current_app.config["VECTOR_DB_URL"]) as conn:
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
        logging.info(f"{search_type} search completed in {elapsed_time:.3f} seconds")
