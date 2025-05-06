# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""All of the configuration for the service is captured here.

All items are loaded,
or have Constants defined here that are loaded into the Flask configuration.
All modules and lookups get their configuration from the Flask config,
rather than reading environment variables directly or by accessing this configuration directly.
"""

import os
import sys
from datetime import timedelta
from dotenv import find_dotenv, load_dotenv

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


class VectorSettings:
    """Vector database configuration settings."""

    def __init__(self, config_dict):
        """Initialize vector settings from config dictionary."""
        self._config = config_dict
    
    @property
    def vector_table_name(self):
        """Get the vector table name."""
        return self._config.get("VECTOR_TABLE")
    
    @property
    def embedding_dimensions(self):
        """Get the embedding dimensions."""
        return self._config.get("EMBEDDING_DIMENSIONS", 768)
    
    @property
    def database_url(self):
        """Get the vector database URL."""
        return self._config.get("VECTOR_DB_URL")
    
    @property
    def time_partition_interval(self):
        """Get the time partition interval."""
        return self._config.get("TIME_PARTITION_INTERVAL")


class SearchSettings:
    """Search configuration settings."""

    def __init__(self, config_dict):
        """Initialize search settings from config dictionary."""
        self._config = config_dict
    
    @property
    def keyword_fetch_count(self):
        """Get the number of keyword search results to fetch."""
        return self._config.get("KEYWORD_FETCH_COUNT")
    
    @property
    def semantic_fetch_count(self):
        """Get the number of semantic search results to fetch."""
        return self._config.get("SEMANTIC_FETCH_COUNT")
    
    @property
    def top_record_count(self):
        """Get the number of top records to return."""
        return self._config.get("TOP_RECORD_COUNT")


class ModelSettings:
    """ML model configuration settings."""

    def __init__(self, config_dict):
        """Initialize model settings from config dictionary."""
        self._config = config_dict
    
    @property
    def cross_encoder_model(self):
        """Get the cross-encoder model name."""
        return self._config.get("CROSS_ENCODER_MODEL")
    
    @property
    def embedding_model_name(self):
        """Get the embedding model name."""
        return self._config.get("EMBEDDING_MODEL_NAME")
    
    @property
    def keyword_model_name(self):
        """Get the keyword model name."""
        return self._config.get("KEYWORD_MODEL_NAME")


def get_named_config(config_name: str = "development"):
    """Return the configuration object based on the name.

    :raise: KeyError: if an unknown configuration is requested
    """
    if config_name in ["production", "staging", "default"]:
        config = ProdConfig()
    elif config_name == "testing":
        config = TestConfig()
    elif config_name == "development":
        config = DevConfig()
    elif config_name == "docker":
        config = DockerConfig()
    else:
        raise KeyError(f"Unknown configuration '{config_name}'")
    return config


class _Config:  # pylint: disable=too-few-public-methods
    """Base class configuration that should set reasonable defaults for all the other configurations."""

    PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

    SECRET_KEY = "a secret"

    TESTING = False
    DEBUG = False

    # Vector Database Configuration
    VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
    TIME_PARTITION_INTERVAL = timedelta(days=7)

    # Search Configuration
    VECTOR_TABLE = os.getenv("VECTOR_TABLE", "document_tags")
    KEYWORD_FETCH_COUNT = int(os.getenv("KEYWORD_FETCH_COUNT", "100"))
    SEMANTIC_FETCH_COUNT = int(os.getenv("SEMANTIC_FETCH_COUNT", "100"))
    TOP_RECORD_COUNT = int(os.getenv("TOP_RECORD_COUNT", "10"))

    # ML Model Configuration
    CROSS_ENCODER_MODEL = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-2-v2")
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-mpnet-base-v2")
    KEYWORD_MODEL_NAME = os.getenv("KEYWORD_MODEL_NAME", "all-mpnet-base-v2")


class DevConfig(_Config):  # pylint: disable=too-few-public-methods
    """Dev Config."""

    TESTING = False
    DEBUG = True


class TestConfig(_Config):  # pylint: disable=too-few-public-methods
    """In support of testing only. Used by the pytest suite."""

    DEBUG = True
    TESTING = True

    # Override with test-specific settings if needed
    VECTOR_DB_URL = os.getenv("TEST_VECTOR_DB_URL", _Config.VECTOR_DB_URL)


class DockerConfig(_Config):  # pylint: disable=too-few-public-methods
    """Docker environment configuration."""
    
    # No specific overrides needed, since VECTOR_DB_URL will be provided in environment


class ProdConfig(_Config):  # pylint: disable=too-few-public-methods
    """Production Config."""

    SECRET_KEY = os.getenv("SECRET_KEY", None)

    if not SECRET_KEY:
        SECRET_KEY = os.urandom(24)
        print("WARNING: SECRET_KEY being set as a one-shot", file=sys.stderr)
