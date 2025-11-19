#!/usr/bin/env python3

# Copyright (c) 2000-2025, Board of Trustees of Leland Stanford Jr. University
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
Base of the lockss.pyclient package (configuration service).
"""

from datetime import datetime
from io import BytesIO
from multipart import MultipartParser

from lockss.pyclient import config
from lockss.pyclient.base import Node, _first, _single_request_template, _paged_request_iterator_template, _CONFIG


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.ConfigApi,
                          config.ConfigApi.get_loaded_url_list)
def config_get_loaded_urls(node: Node) -> list[str]:
    pass


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.ConfigApi,
                          config.ConfigApi.get_platform_config)
def config_get_platform_config(node: Node) -> config.PlatformConfigurationWsResult:
    pass


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.StatusApi,
                          config.StatusApi.get_status,
                          needs_auth=False)
def config_get_status(node: Node) -> config.ApiStatus:
    pass


def config_get_section(node: Node,
                       section_name: str,
                       if_match: str = None,
                       if_modified_since: str = None,
                       if_none_match: str = None,
                       if_unmodified_since: str = None) -> MultipartParser:
    @_single_request_template(Node.make_config_conf,
                              config.ApiClient,
                              config.ConfigApi,
                              config.ConfigApi.get_section_config,
                              remove_kwargs=['if_match', 'if_modified_since', 'if_none_match', 'if_unmodified_since'])
    def _config_get_section(node: Node,
                            section_name: str,
                            if_match: str = None,
                            if_modified_since: str = None,
                            if_none_match: str = None,
                            if_unmodified_since: str = None) -> str:
        pass
    result: str = _config_get_section(node,
                                      section_name,
                                      if_match=if_match,
                                      if_modified_since=if_modified_since,
                                      if_none_match=if_none_match,
                                      if_unmodified_since=if_unmodified_since)
    # Result is of type str but seems to be a repr() string "b'...'"
    boundary = (byte_input := eval(result)).partition(b'\r\n')[0].partition(b'--')[2]
    return MultipartParser(BytesIO(byte_input), boundary)


def config_get_url(node: Node,
                   url: str,
                   if_match: str = None,
                   if_modified_since: str = None,
                   if_none_match: str = None,
                   if_unmodified_since: str = None) -> MultipartParser:
    @_single_request_template(Node.make_config_conf,
                              config.ApiClient,
                              config.ConfigApi,
                              config.ConfigApi.get_url_config,
                              remove_kwargs=['if_match', 'if_modified_since', 'if_none_match', 'if_unmodified_since'])
    def _config_get_url(node: Node,
                        url: str,
                        if_match: str = None,
                        if_modified_since: str = None,
                        if_none_match: str = None,
                        if_unmodified_since: str = None) -> str:
        pass
    result: str = _config_get_url(node,
                                  url,
                                  if_match=if_match,
                                  if_modified_since=if_modified_since,
                                  if_none_match=if_none_match,
                                  if_unmodified_since=if_unmodified_since)
    # Result is of type str but seems to be a repr() string "b'...'"
    boundary = (byte_input := eval(result)).partition(b'\r\n')[0].partition(b'--')[2]
    return MultipartParser(BytesIO(byte_input), boundary)


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.UsersApi,
                          config.UsersApi.get_user_account)
def config_get_user_account(node: Node,
                            username: str) -> str:
    pass


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.UsersApi,
                          config.UsersApi.get_user_account_names)
def config_get_usernames(node: Node) -> list[str]:
    pass


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.UtilsApi,
                          config.UtilsApi.normalize_url)
def config_normalize_url(node: Node,
                         url: str) -> list[str]:
    pass


@_single_request_template(Node.make_config_conf,
                          config.ApiClient,
                          config.ConfigApi,
                          config.ConfigApi.get_last_update_time)
def config_last_update_time(node: Node,
                            url: str) -> datetime:
    pass


if __name__ == '__main__':
    node = Node('localhost', 'lockss-u')
    print(f'Demo for {node.get_host()}:{node.get_config_port()}')
    status = config_get_status(node)
    print(f'config_get_status: {status.to_dict()}')
    print(f'config_get_usernames: {config_get_usernames(node)}')
    print(f'config_get_loaded_urls: {config_get_loaded_urls(node)}')
    cfgurl = 'http://props.lockss.org:8001/demo/lockss.xml'
    cfgurlmp = config_get_url(node, cfgurl)
    print(f'config_get_url {cfgurl}:\n{cfgurlmp.get('configFile').value}')
    section = 'cluster'
    sectionmp = config_get_section(node, section)
    print(f'config_get_section {section}:\n{sectionmp.get('configFile').value}')
    print(f'config_get_platform_config: {config_get_platform_config(node).to_dict()}')
    print(f'config_last_update_time: {config_last_update_time(node)}')
