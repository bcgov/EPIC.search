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
PostgreSQL Database Package for Processing Logs.

This package provides interfaces for interacting with the PostgreSQL database
that stores document processing logs. It includes utilities for session management,
database initialization, and the ProcessingLog model for tracking document
processing status.
"""

from .db_utils import get_session, init_db
from .processing_logs import ProcessingLog
