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

"""
PostgreSQL Vector Database Package.

This package provides interfaces for interacting with PostgreSQL databases
that use the pgvector extension for storing and querying vector embeddings.
It includes a VectorStore class for handling vector operations and utility
functions for initializing the vector database tables and indexes.
"""


from .vector_db_utils import init_vec_db
from .vector_store import VectorStore