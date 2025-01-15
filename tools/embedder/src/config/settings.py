import logging
import os
from datetime import timedelta
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


class LLMCommonSettings(BaseModel):
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    max_retries: int = 3


class MistralSettings(LLMCommonSettings):
    api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    default_model: str = Field(default="mistral")


class EmbeddingModelSettings(BaseModel):
    model_name: str = Field(default="nomic-embed-text")

class DatabaseSettings(BaseModel):
    service_url: str = Field(default_factory=lambda: os.getenv("VECTOR_DB_URL"))


class VectorStoreSettings(BaseModel):
    table_name: str = os.environ.get("INDEX_TABLE_NAME")
    embedding_dimensions: int = 768
    time_partition_interval: timedelta = timedelta(days=7)


class Settings(BaseModel):
    embedding_model: EmbeddingModelSettings = Field(default_factory=EmbeddingModelSettings)
    llm_settings: MistralSettings = Field(default_factory=MistralSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    setup_logging()
    return settings