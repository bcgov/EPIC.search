from typing import List, Optional
from src.config import get_settings

from timescale_vector import client

class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.vector_settings = self.settings.vector_store
        self.embedding_model = self.settings.embedding_model
        self._vec_clients = {}
    def get_client_for_table(self, table_name: str, embedding_dimensions: Optional[int] = None) -> client.Sync:
        if table_name not in self._vec_clients:
            if embedding_dimensions is None:
                embedding_dimensions = self.vector_settings.embedding_dimensions

            vec_client = client.Sync(
                self.settings.database.service_url,
                table_name,
                embedding_dimensions,
                time_partition_interval=self.vector_settings.time_partition_interval
            )
            self._vec_clients[table_name] = vec_client
        return self._vec_clients[table_name]
    


    def create_table(self, table_name: str, embedding_dimensions: Optional[int] = None) -> None:
        vec_client = self.get_client_for_table(table_name, embedding_dimensions)
        vec_client.create_tables()

    def create_index(self, table_name: str) -> None:
        vec_client = self.get_client_for_table(table_name)
        vec_client.create_embedding_index(client.DiskAnnIndex())


    def drop_index(self, table_name: str) -> None:
        vec_client = self.get_client_for_table(table_name)
        vec_client.drop_embedding_index()

    def upsert(self, table_name: str, records: List[dict]) -> None:
        vec_client = self.get_client_for_table(table_name)
        vec_client.upsert(records)
    
    def delete_by_metadata(self, table_name: str, metadata_filters: dict) -> None:
        vec_client = self.get_client_for_table(table_name)
        vec_client.delete_by_metadata(metadata_filters)

    
