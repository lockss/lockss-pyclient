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

from collections.abc import Callable, Iterator
from functools import partialmethod
from typing import Any, Optional, TypeVar, Union, cast, TYPE_CHECKING

from lockss.pybasic.nodeutil import NodeSpec2

from . import config, crawler, md, poller, rs
from ._interface import _LockssClientInterface

# Avoid circular import
if TYPE_CHECKING:
    from ._core import LockssClient


_ApiConf = Union[
    config.Configuration,
    crawler.Configuration,
    md.Configuration,
    poller.Configuration,
    rs.Configuration
]


_ApiClient = Union[
    config.ApiClient,
    crawler.ApiClient,
    md.ApiClient,
    poller.ApiClient,
    rs.ApiClient
]


_ApiInstance = Union[
    config.StatusApi,
    crawler.StatusApi,
    md.StatusApi,
    poller.ServiceApi,
    rs.AusApi, rs.RepoApi, rs.StatusApi,
]


_PageInfoResult = Union[
    rs.AuidPageInfo
]


_ApiResult = TypeVar('_ApiResult')


class _LockssClient2(_LockssClientInterface):

    _client: LockssClient
    _node_spec: NodeSpec2
    _ul: Optional[Callable[[], str]] = None
    _pl: Optional[Callable[[], str]] = None

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

    def get_auids_page(self,
                       namespace: str,
                       limit: Optional[int] = None,
                       continuation_token: Optional[str] = None,
                       **kwargs) -> rs.AuidPageInfo:
        return self._generic_single_repository_action(rs.AusApi,
                                                      rs.AusApi.get_aus,
                                                      namespace=namespace,
                                                      limit=limit,
                                                      continuation_token=continuation_token,
                                                      **kwargs)

    def get_auids(self, namespace: str, **kwargs) -> list[str]:
        return list(self._generic_paged_repository_action(rs.AusApi,
                                                          rs.AusApi.get_aus,
                                                          lambda p: cast(rs.AuidPageInfo, p).auids,
                                                          namespace=namespace))

    def get_namespaces(self, **kwargs) -> list[str]:
        return self._generic_single_repository_action(rs.RepoApi, rs.RepoApi.get_namespaces)

    def get_repository_service_status(self, **kwargs) -> rs.ApiStatus:
        return self._generic_single_repository_action(rs.StatusApi, rs.StatusApi.get_status)

    def get_supported_checksum_algorithms(self, **kwargs) -> list[str]:
        return self._generic_single_repository_action(rs.RepoApi, rs.RepoApi.get_supported_checksum_algorithms)

    #
    # CONFIGURATION
    #

    def get_configuration_service_status(self, **kwargs) -> config.ApiStatus:
        return self._generic_single_configuration_action(config.StatusApi, config.StatusApi.get_status)

    #
    # POLLER
    #

    def get_poller_service_status(self, **kwargs) -> poller.ApiStatus:
        return self._generic_single_poller_action(poller.ServiceApi, poller.ServiceApi.get_status)

    #
    # CRAWLER
    #

    def get_crawler_service_status(self, **kwargs) -> crawler.ApiStatus:
        return self._generic_single_poller_action(crawler.StatusApi,
                                                  lambda api: api.get_status())

    #
    # METADATA
    #

    def get_metadata_service_status(self, **kwargs) -> md.ApiStatus:
        return self._generic_single_poller_action(md.StatusApi,
                                                  lambda api: api.get_status())

    #
    # PROTECTED
    #

    def _generic_single_action(self,
                               api_conf_supplier: Callable[[], _ApiConf],
                               host_supplier: Callable[[_LockssClient2], str],
                               api_client_supplier: Callable[[_ApiConf], _ApiClient],
                               api_instance_supplier: Callable[[_ApiClient], _ApiInstance],
                               api_action: Callable[[_ApiInstance, ...], _ApiResult],
                               *args,
                               **kwargs) -> _ApiResult:
        conf: _ApiConf = api_conf_supplier()
        conf.host = host_supplier(self)
        if self._ul is not None:
            conf.username = self._ul()
        if self._pl is not None:
            conf.password = self._pl()
        api_client: _ApiClient = api_client_supplier(conf)
        api_instance: _ApiInstance = api_instance_supplier(api_client)
        api_result: _ApiResult = api_action(api_instance, *args, **kwargs)
        return api_result

    _generic_single_repository_action = partialmethod(_generic_single_action,
                                                      rs.Configuration,
                                                      lambda slf: slf._node_spec.get_repository_host(),
                                                      rs.ApiClient)

    _generic_single_configuration_action = partialmethod(_generic_single_action,
                                                         config.Configuration,
                                                         lambda slf: slf._node_spec.get_configuration_host(),
                                                         config.ApiClient)

    _generic_single_poller_action = partialmethod(_generic_single_action,
                                                  poller.Configuration,
                                                  lambda slf: slf._node_spec.get_poller_host(),
                                                  poller.ApiClient)

    def _generic_paged_action(self,
                              api_conf_supplier: Callable[[], _ApiConf],
                              host_supplier: Callable[[_LockssClient2], str],
                              api_client_supplier: Callable[[_ApiConf], _ApiClient],
                              api_instance_supplier: Callable[[_ApiClient], _ApiInstance],
                              api_action: Callable[[_ApiInstance, ...], _PageInfoResult],
                              item_accessor: Callable[[_PageInfoResult], Iterator[_ApiResult]],
                              *args,
                              **kwargs) -> Iterator[_ApiResult]:
        newkwargs: dict[str, Any] = kwargs.copy()
        token = None
        while True:
            if token:
                newkwargs['continuation_token'] = token
            else:
                newkwargs.pop('continuation_token', None)
            if newkwargs.get('limit') is None:
                kwargs['limit'] = 100 ### FIXME
            result_page: _PageInfoResult = self._generic_single_action(api_conf_supplier,
                                                                       host_supplier,
                                                                       api_client_supplier,
                                                                       api_instance_supplier,
                                                                       api_action,
                                                                       *args,
                                                                       **newkwargs)
            token = result_page.page_info.continuation_token
            for result in item_accessor(result_page):
                yield result
            if token is None:
                break

    _generic_paged_repository_action = partialmethod(_generic_paged_action,
                                                      rs.Configuration,
                                                      lambda slf: slf._node_spec.get_repository_host(),
                                                      rs.ApiClient)

    _generic_paged_configuration_action = partialmethod(_generic_paged_action,
                                                         config.Configuration,
                                                         lambda slf: slf._node_spec.get_configuration_host(),
                                                         config.ApiClient)

    _generic_paged_poller_action = partialmethod(_generic_paged_action,
                                                  poller.Configuration,
                                                  lambda slf: slf._node_spec.get_poller_host(),
                                                  poller.ApiClient)

