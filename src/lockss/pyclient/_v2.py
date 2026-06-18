#!/usr/bin/env python3

# Copyright (c) 2000-2026, Board of Trustees of Leland Stanford Jr. University
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
LOCKSS 2.x client implementation.
"""

from typing import TYPE_CHECKING

from collections.abc import Callable
from typing import Optional

from . import rs
from ._interface import _LockssClientInterface

# Avoid circular import
if TYPE_CHECKING:
    from ._core import LockssClient


class _LockssClient2(_LockssClientInterface):

    def __init__(self, client: LockssClient) -> None:
        self._client: LockssClient = client
        self._ul: Callable[[], Optional[str]] = lambda: None
        self._pl: Callable[[], Optional[str]] = lambda: None

    def authenticate(self, u: str, p: str) -> _LockssClient2:
        self._ul = lambda: u
        self._pl = lambda: p
        return self

    #
    # REPOSITORY
    #

    def get_repository_service_status(self) -> rs.ApiStatus:
        conf: rs.Configuration = rs.Configuration()
        conf.host = f'{(ns := self._client.get_node_spec()).host}:{ns.repository}'
        api_client: rs.ApiClient = rs.ApiClient(conf)
        api_instance: rs.StatusApi = rs.StatusApi(api_client)
        api_result: rs.ApiStatus = api_instance.get_status()
        return api_result
