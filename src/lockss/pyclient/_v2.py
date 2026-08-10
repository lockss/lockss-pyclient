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

from lockss.pybasic.nodeutil import NodeSpec2

from . import config, crawler, md, poller, rs
from ._interface import _LockssClientInterface

# Avoid circular import
if TYPE_CHECKING:
    from ._core import LockssClient


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
    config.StatusApi,
    poller.ServiceApi,
    rs.StatusApi
]


_ApiInstanceSupplier: TypeAlias = Callable[[_ApiClientT], _ApiInstanceT]


_ApiResult = TypeVar('_ApiResult')


_StrSupplier: TypeAlias = Callable[[], str]


class _LockssClient2(_LockssClientInterface):

    _client: LockssClient
    _node_spec: NodeSpec2
    _ul: Callable[[], str]
    _pl: Callable[[], str]

    def __init__(self, client: LockssClient, node_spec: NodeSpec2) -> None:
        self._client = client
        self._node_spec = node_spec

    def authenticate(self, u: str, p: str) -> _LockssClient2:
        self._ul = lambda: u
        self._pl = lambda: p
        return self

    #
    # REPOSITORY
    #

    def get_repository_service_status(self) -> rs.ApiStatus:
        return self._generic_single_repository_action(rs.StatusApi,
                                                      lambda api: api.get_status())

    #
    # CONFIGURATION
    #

    def get_configuration_service_status(self) -> config.ApiStatus:
        return self._generic_single_configuration_action(config.StatusApi,
                                                         lambda api: api.get_status())

    #
    # POLLER
    #

    def get_poller_service_status(self) -> poller.ApiStatus:
        return self._generic_single_poller_action(poller.ServiceApi,
                                                  lambda api: api.get_status())

    #
    # CRAWLER
    #

    def get_crawler_service_status(self) -> crawler.ApiStatus:
        return self._generic_single_poller_action(crawler.StatusApi,
                                                  lambda api: api.get_status())

    #
    # METADATA
    #

    def get_metadata_service_status(self) -> md.ApiStatus:
        return self._generic_single_poller_action(md.StatusApi,
                                                  lambda api: api.get_status())

    #
    # PROTECTED
    #

    def _generic_single_action(self,
                               api_conf_supplier: _ApiConfSupplier,
                               host_supplier: _StrSupplier,
                               api_client_supplier: _ApiClientSupplier,
                               api_instance_supplier: _ApiInstanceSupplier,
                               api_action: Callable[[_ApiInstanceT], _ApiResult]) -> _ApiResult:
        conf: _ApiConfT = api_conf_supplier()
        conf.host = host_supplier()
        api_client: _ApiClientT = api_client_supplier(conf)
        api_instance: _ApiInstanceT = api_instance_supplier(api_client)
        api_result: _ApiResult = api_action(api_instance)
        return api_result

    def _generic_single_repository_action(self,
                                          api_instance_supplier: _ApiInstanceSupplier,
                                          api_action: Callable[[_ApiInstanceT], _ApiResult]) -> _ApiResult:
        return self._generic_single_action(rs.Configuration,
                                           self._node_spec.get_repository_host,
                                           rs.ApiClient,
                                           api_instance_supplier,
                                           api_action)

    def _generic_single_configuration_action(self,
                                             api_instance_supplier: _ApiInstanceSupplier,
                                             api_action: Callable[[_ApiInstanceT], _ApiResult]) -> _ApiResult:
        return self._generic_single_action(config.Configuration,
                                           self._node_spec.get_configuration_host,
                                           config.ApiClient,
                                           api_instance_supplier,
                                           api_action)

    def _generic_single_poller_action(self,
                                      api_instance_supplier: _ApiInstanceSupplier,
                                      api_action: Callable[[_ApiInstanceT], _ApiResult]) -> _ApiResult:
        return self._generic_single_action(poller.Configuration,
                                           self._node_spec.get_poller_host,
                                           poller.ApiClient,
                                           api_instance_supplier,
                                           api_action)

