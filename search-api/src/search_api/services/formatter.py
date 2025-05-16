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
"""Formatter service for preparing data for LLM processing."""

import numpy as np


def format_llm_input(documents):
    """
    Format document data for LLM input.
    
    Transforms the raw document data into a format suitable for LLM processing,
    extracting project name and text content.
    
    Args:
        documents (list): List of document data to be formatted
        
    Returns:
        list: Formatted documents with project_name and text fields
    """
    data = np.array(documents) 
    output = [
                {
                    "project_name": row[4].get("project_name", ""),
                    "text": row[1]
                }
                for row in data
            ]
    return output