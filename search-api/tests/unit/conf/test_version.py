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

"""Tests to assure the version utilities.

Test-Suite to ensure that the version utilities are working as expected.
"""
from search_api.utils import run_version
from search_api.version import __version__


def test_get_version():
    """Assert thatThe version is returned correctly."""
    rv = run_version.get_run_version()
    assert rv == __version__
