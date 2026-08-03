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

from typing import TypeAlias, TypeVar, Union, TYPE_CHECKING

from collections.abc import Callable

from lockss.pybasic.nodeutil import NodeSpec

from . import config, crawler, md, poller, rs

# Avoid circular import
if TYPE_CHECKING:
    from ._core import _BaseLockssClient, LockssClient


_ApiConfT = Union[
    config.Configuration,
    crawler.Configuration,
    md.Configuration,
    poller.Configuration,
    rs.Configuration
]


_ApiConfSupplier: TypeAlias = Callable[[], _ApiConfT]


_ApiClientT = Union[
    config.ApiClient,
    crawler.ApiClient,
    md.ApiClient,
    poller.ApiClient,
    rs.ApiClient
]


_ApiClientSupplier: TypeAlias = Callable[[_ApiConfT], _ApiClientT]


_ApiInstanceT: TypeAlias = Union[
    rs.StatusApi
]


_ApiInstanceSupplier: TypeAlias = Callable[[_ApiClientT], _ApiInstanceT]


_ApiResult = TypeVar('_ApiResult')


_StrSupplier: TypeAlias = Callable[[], str]


class _LockssClient2(_BaseLockssClient):

    _ul: Callable[[], str]
    _pl: Callable[[], str]

    def __init__(self, client: LockssClient, node_spec: NodeSpec) -> None:
        super().__init__(client, node_spec)

    def authenticate(self, u: str, p: str) -> _LockssClient2:
        self._ul = lambda: u
        self._pl = lambda: p
        return self

    #
    # REPOSITORY
    #

    def get_repository_service_status(self) -> rs.ApiStatus:
        return self._generic_single_repository_action()

    #
    # PROTECTED
    #

    def _generic_single_action(self,
                               api_conf_supplier: _ApiConfSupplier,
                               host_supplier: _StrSupplier,
                               api_client_supplier: _ApiClientSupplier,
                               api_instance_supplier: _ApiInstanceSupplier) -> _ApiResult:
        conf: _ApiConfT = api_conf_supplier()
        conf.host = host_supplier()
        api_client: _ApiClientT = api_client_supplier(conf)
        api_instance: _ApiInstanceT = api_instance_supplier(api_client)
        api_result: _ApiResult = api_instance.get_status()
        return api_result

    def _generic_single_repository_action(self) -> _ApiResult:
        return self._generic_single_action(rs.Configuration,
                                           lambda: f'{(ns := self._node_spec).protocol}://{ns.host}:{ns.repository}',
                                           rs.ApiClient,
                                           rs.StatusApi)

