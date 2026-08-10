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
Core of the lockss.pyclient package.
"""

from typing import cast

from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.nodeutil import NodeIdentifier, NodeSpec, NodeSpec1, NodeSpec2, NodeSpec12Pair, NodeTypeEnum

from . import config, crawler, md, poller, rs
from ._interface import _LockssClientInterface
from ._v1 import _LockssClient1
from ._v2 import _LockssClient2
from ._v1_v2_pair import _LockssClient12Pair


class LockssClient(_LockssClientInterface):
    """
    A client for either LOCKSS 1.x, 2.x, or a 1.x/2.x migration pair.
    """

    _impl: _LockssClientInterface
    _node_spec: NodeSpec

    def __init__(self, node_spec: NodeSpec):
        self._node_spec = node_spec.model_copy()
        match typ := node_spec.type:
            case NodeTypeEnum.V1.value:
                self._impl = _LockssClient1(self, cast(NodeSpec1, self._node_spec))
            case NodeTypeEnum.V2.value:
                self._impl = _LockssClient2(self, cast(NodeSpec2, self._node_spec))
            case NodeTypeEnum.V1_V2_MIGRATION_PAIR.value:
                self._impl = _LockssClient12Pair(self, cast(NodeSpec12Pair, self._node_spec))
            case _:
                raise InternalError from ValueError(typ)

    def authenticate(self, u: str, p: str) -> LockssClient:
        self._impl.authenticate(u, p)
        return self

    def get_id(self) -> NodeIdentifier:
        """
        Returns this client's node identifier, from the node spec.

        :return: This client's node identifier.
        :rtype: NodeIdentifier
        """
        return self._node_spec.id

    #
    # REPOSITORY
    #

    def get_repository_service_status(self) -> rs.ApiStatus:
        return self._impl.get_repository_service_status()

    #
    # CONFIGURATION
    #

    def get_configuration_service_status(self) -> config.ApiStatus:
        return self._impl.get_configuration_service_status()

    #
    # POLLER
    #

    def get_poller_service_status(self) -> poller.ApiStatus:
        return self._impl.get_poller_service_status()

    #
    # CRAWLER
    #

    def get_crawler_service_status(self) -> crawler.ApiStatus:
        return self._impl.get_crawler_service_status()


    #
    # METADATA
    #

    def get_metadata_service_status(self) -> md.ApiStatus:
        return self._impl.get_metadata_service_status()
