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
Services Package for Document Processing and Embedding.

This package contains the core service modules that handle document processing,
text extraction, vector embedding generation, and data storage operations.
Each service module focuses on a specific aspect of the document processing pipeline,
from loading files to embedding text and storing vectors.
"""

# Import all service modules for easier access
from .api_utils import get_project_by_id, get_projects, get_files_for_project
from .bert_keyword_extractor import get_keywords
from .data_formatter import format_metadata, aggregate_tags_by_chunk
from .embedding import get_embedding
from .loader import load_data
from .logger import log_processing_result, get_processing_logs, load_completed_files, load_incomplete_files
from .markdown_reader import read_as_pages
from .markdown_splitter import chunk_markdown_text
from .processor import process_files
from .s3_reader import read_file_from_s3
from .tag_extractor import get_tags, explicit_and_semantic_search_large_document