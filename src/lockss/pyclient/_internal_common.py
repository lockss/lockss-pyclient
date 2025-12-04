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
Base of the lockss.pyclient package.
"""

# Remove in Python 3.14; see https://stackoverflow.com/a/33533514
from __future__ import annotations

from collections.abc import Callable, Iterable
from getpass import getpass
from importlib import resources
from io import BytesIO
from typing import Any, ClassVar, Optional, TypeVar, Union

from jsonpath import query
from multipart import MultipartParser
import yaml

from . import config, crawler, md, poller, rs


YamlT = Any


def _load_swagger(package) -> YamlT:
    with resources.path(package, 'swagger.yaml') as p:
        with p.open('rb') as f:
            return yaml.safe_load(f)


_CONFIG = _load_swagger(config)


_CRAWLER = _load_swagger(crawler)


_MD = _load_swagger(md)


_POLLER = _load_swagger(poller)


_RS = _load_swagger(rs)


def _first(data: YamlT, json_path: str) -> Any:
    return query(json_path, data).first_one().value


def _param_default(data: YamlT, path: str, method: str, param_name: str) -> Any:
    return _first(data, f'$.paths["{path}"].{method}.parameters[?(@.name == "{param_name}")].schema.default')


def _schema_default(data: YamlT, schema_name: str) -> Any:
    return _first(_RS, f'$.components.schemas.{schema_name}.default')


__JSON_PATH_DEFAULT_PORT = '$.servers[0].variables.port.default'


CONFIG_DEFAULT_PORT: int = _first(_CONFIG, __JSON_PATH_DEFAULT_PORT)


CRAWLER_DEFAULT_PORT: int = _first(_CRAWLER, __JSON_PATH_DEFAULT_PORT)


MD_DEFAULT_PORT: int = _first(_MD, __JSON_PATH_DEFAULT_PORT)


POLLER_DEFAULT_PORT: int = _first(_POLLER, __JSON_PATH_DEFAULT_PORT)


RS_DEFAULT_PORT: int = _first(_RS, __JSON_PATH_DEFAULT_PORT)


ConfT = Union[
    config.Configuration,
    crawler.Configuration,
    md.Configuration,
    poller.Configuration,
    rs.Configuration,
]


ConfSupplier = Callable[[], ConfT]


PortGetter = Callable[..., int]


StrSupplier = Callable[[], str]


class Node(object):

    DEFAULT_PROTOCOL: ClassVar[str] = 'http'

    # DECORATOR
    @staticmethod
    def _make_conf_template(make_conf: ConfSupplier,
                            get_port: PortGetter):
        def decorate(f):
            def decorated_make_conf(self: Node,
                                    needs_auth: bool = True) -> ConfT:
                conf = make_conf()
                conf.host = f'{self.get_host()}:{get_port(self)}'
                if needs_auth:
                    conf.username = self.get_username()
                    conf.password = self.get_password()()
                return conf
            return decorated_make_conf
        return decorate

    # DECORATOR
    @staticmethod
    def _set_port_template(port_name: str):
        def decorate(f):
            def decorated_set_port(self: Node,
                                   port: int) -> Node:
                setattr(self, port_name, port)
                return self
            return decorated_set_port
        return decorate

    # DECORATOR
    @staticmethod
    def _get_port_template(port_name: str,
                           default_port: int):
        def decorate(f):
            def decorated_get_port(self: Node) -> int:
                return getattr(self, port_name, default_port)
            return decorated_get_port
        return decorate

    def __init__(self,
                 node_reference: str,
                 username: Optional[str] = None,
                 password: Optional[StrSupplier] = None,
                 interactive: bool = True,
                 config_port: int = CONFIG_DEFAULT_PORT,
                 crawler_port: int = CRAWLER_DEFAULT_PORT,
                 md_port: int = MD_DEFAULT_PORT,
                 poller_port: int = POLLER_DEFAULT_PORT,
                 rs_port: int = RS_DEFAULT_PORT):
        super().__init__()
        self._host: str = Node._compute_host(node_reference)
        self._username: Optional[str] = username
        self._password: Optional[StrSupplier] = password
        self._interactive: bool = interactive
        self._config_port = config_port
        self._crawler_port = crawler_port
        self._md_port: int = md_port
        self._poller_port: int = poller_port
        self._rs_port: int = rs_port

    @_get_port_template('_config_port', CONFIG_DEFAULT_PORT)
    def get_config_port(self: Node) -> int:
        pass

    @_get_port_template('_crawler_port', CRAWLER_DEFAULT_PORT)
    def get_crawler_port(self: Node) -> int:
        pass

    def get_host(self) -> str:
        return self._host

    @_get_port_template('_md_port', MD_DEFAULT_PORT)
    def get_md_port(self: Node) -> int:
        pass

    @_get_port_template('_poller_port', POLLER_DEFAULT_PORT)
    def get_poller_port(self: Node) -> int:
        pass

    @_get_port_template('_rs_port', RS_DEFAULT_PORT)
    def get_rs_port(self: Node) -> int:
        pass

    def get_username(self) -> str:
        return self._username

    def get_password(self) -> Optional[StrSupplier]:
        if not self._password:
            if not self._interactive:
                raise RuntimeError('interactive prompts not allowed')
            _p = getpass(f'Password ({self.get_host().partition("://")[2]}): ')
            self._password = lambda: _p
        return self._password

    @_make_conf_template(config.Configuration, get_config_port)
    def make_config_conf(self, needs_auth: bool = True) -> config.Configuration:
        pass

    @_make_conf_template(crawler.Configuration, get_crawler_port)
    def make_crawler_conf(self, needs_auth: bool = True) -> crawler.Configuration:
        pass

    @_make_conf_template(md.Configuration, get_md_port)
    def make_md_conf(self, needs_auth: bool = True) -> md.Configuration:
        pass

    @_make_conf_template(poller.Configuration, get_poller_port)
    def make_poller_conf(self, needs_auth: bool = True) -> poller.Configuration:
        pass

    @_make_conf_template(rs.Configuration, get_rs_port)
    def make_rs_conf(self, needs_auth: bool = True) -> rs.Configuration:
        pass

    @_set_port_template('_config_port')
    def set_config_port(self, port: int) -> Node:
        pass

    @_set_port_template('_crawler_port')
    def set_crawler_port(self, port: int) -> Node:
        pass

    @_set_port_template('_md_port')
    def set_md_port(self, port: int) -> Node:
        pass

    @_set_port_template('_poller_port')
    def set_poller_port(self, port: int) -> Node:
        pass

    @_set_port_template('_rs_port')
    def set_rs_port(self, port: int) -> Node:
        pass

    def set_username(self, username: str) -> Node:
        self._username = username
        return self

    @staticmethod
    def _compute_host(node_reference: str) -> str:
        if node_reference.endswith('/'):
            node_reference = node_reference[:-1]
        x, y, z = node_reference.rpartition(':')
        if z.isdigit():
            node_reference = x # Ignore port if passed in
        if '://' not in node_reference:
            node_reference = f'{Node.DEFAULT_PROTOCOL}://{node_reference}'
        return node_reference


ConfFunction = Callable[..., ConfT]


ApiClientT = Union[
    config.ApiClient,
    crawler.ApiClient,
    md.ApiClient,
    poller.ApiClient,
    rs.ApiClient,
]


ApiClientFunction = Callable[..., ApiClientT]


ApiInstanceT = Union[
    config.AusApi, config.ConfigApi, config.PluginsApi, config.StatusApi, config.TdbApi, config.UsersApi, config.UtilsApi,
    crawler.CrawlersApi, crawler.CrawlsApi, crawler.JobsApi, crawler.StatusApi, crawler.WsApi,
    md.MdupdatesApi, md.MetadataApi, md.StatusApi, md.UrlsApi,
    poller.ExportApi, poller.HashApi, poller.ImportApi, poller.PollDetailApi, poller.PollerPollsApi, poller.RepoApi, poller.ServiceApi, poller.VoterPollsApi,
    rs.ArtifactsApi, rs.AusApi, rs.RepoApi, rs.StatusApi, rs.WaybackApi,
]


ApiInstanceFunction = Callable[[ApiClientT], ApiInstanceT]


ApiResultT = TypeVar('ApiResultT')


ApiResultFunction = Callable[..., ApiResultT]


ResultT = TypeVar('ResultT')


ResultFunction = Callable[[ApiResultT], ResultT]


def _single_request_template(make_conf: ConfFunction,
                             make_api_client: ApiClientFunction,
                             make_api_instance: ApiInstanceFunction,
                             api_operation: ApiResultFunction,
                             needs_auth: bool = True,
                             remove_kwargs: Optional[list[str]] = None,
                             transform_result: ResultFunction = lambda x: x,
                             transform_raw_result: Optional[Any] = None):
    def decorate(f):
        def decorated_single_request(node: Node, *args, **kwargs) -> ResultT:
            if needs_auth:
                conf: ConfT = make_conf(node)
                api_client: ApiClientT = make_api_client(conf, "Authorization", conf.get_basic_auth_token())
            else:
                conf: ConfT = make_conf(node, needs_auth=False)
                api_client: ApiClientT = make_api_client(conf)
            api_instance: ApiInstanceT = make_api_instance(api_client)
            for remove in [key for key, val in kwargs.items() if key in (remove_kwargs or []) and val is None]:
                kwargs.pop(remove, None)
            if transform_raw_result:
                kwargs['_preload_content'] = False
            api_response: ApiResultT = api_operation(api_instance, *args, **kwargs)
            if transform_raw_result:
                result = api_client.deserialize(api_response, transform_raw_result)
            else:
                result: ResultT = transform_result(api_response)
            return result
        return decorated_single_request
    return decorate


PageInfoResultT = Union[
    config.AuConfigPageInfo,
    crawler.CrawlPager, crawler.JobPager, crawler.UrlPager,
    md.AuMetadataPageInfo, md.JobPageInfo,
    poller.PollerPageInfo, poller.RepairPageInfo, poller.UrlPageInfo,
    rs.ArtifactPageInfo, rs.AuidPageInfo,
]


PageInfoResultFunction = Callable[..., PageInfoResultT]


def _paged_request_iterator_template(single_request: PageInfoResultFunction,
                                     remove_kwargs: Optional[list[str]] = None):
    def decorate(f):
        def decorated_paged_request_iterator(*args, **kwargs) -> Iterable[PageInfoResultT]:
            for remove in [key for key, val in kwargs.items() if key in (remove_kwargs or []) and val is None]:
                kwargs.pop(remove, None)
            token = None
            while True:
                if token:
                    kwargs['continuation_token'] = token
                else:
                    kwargs.pop('continuation_token', None)
                if kwargs.get('limit') is None:
                    kwargs['limit'] = 100
                result: PageInfoResultT = single_request(*args, **kwargs)
                token = result.page_info.continuation_token
                yield result
                if token is None:
                    break
        return decorated_paged_request_iterator
    return decorate


def bytes_repr_to_multipart(bytes_repr: str) -> MultipartParser:
    byte_input: bytes = eval(bytes_repr)
    boundary: bytes = byte_input.partition(b'\r\n')[0].partition(b'--')[2]
    return MultipartParser(BytesIO(byte_input), boundary)


def bytes_repr_to_string(bytes_repr: str) -> str:
    byte_input: bytes = eval(bytes_repr)
    return byte_input.decode()
