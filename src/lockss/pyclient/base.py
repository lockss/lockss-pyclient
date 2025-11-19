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
from jsonpath import query
from multipart import MultipartParser
from typing import Any, ClassVar, Optional, TypeVar, Union
import yaml

from lockss.pyclient import config, crawler, md, poller, rs


YamlT = Any


def _load_swagger(package) -> YamlT:
    with resources.path(package, 'swagger.yaml') as p:
        with p.open('rb') as f:
            return yaml.safe_load(f)


__CONFIG = _load_swagger(config)


__CRAWLER = _load_swagger(crawler)


__MD = _load_swagger(md)


__POLLER = _load_swagger(poller)


__RS = _load_swagger(rs)


def _first(data: YamlT, json_path: str) -> Any:
    return query(json_path, data).first_one().value


RS_DEFAULT_PORT: int = _first(__RS, '$.servers[0].variables.port.default')


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
                 rs_port: int = RS_DEFAULT_PORT):
        super().__init__()
        self._host: str = Node._compute_host(node_reference)
        self._username: Optional[str] = username
        self._password: Optional[StrSupplier] = password
        self._interactive: bool = interactive
        self._rs_port: int = rs_port

    def get_host(self) -> str:
        return self._host

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

    @_make_conf_template(rs.Configuration, get_rs_port)
    def make_repo_conf(self, needs_auth: bool = True) -> rs.Configuration:
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


ResultT = TypeVar('ResultT')


ResultFunction = Callable[..., ResultT]


def _single_request_template(make_conf: ConfFunction,
                             make_api_client: ApiClientFunction,
                             make_api_instance: ApiInstanceFunction,
                             api_operation: ResultFunction,
                             needs_auth: bool = True,
                             remove_kwargs: Optional[list[str]] = None):
    def decorate(f):
        def decorated_single_request(node: Node, *args, **kwargs) -> ResultT:
            if needs_auth:
                conf = make_conf(node)
                api_client = make_api_client(conf, "Authorization", conf.get_basic_auth_token())
            else:
                conf = make_conf(node, needs_auth=False)
                api_client = make_api_client(conf)
            api_instance = make_api_instance(api_client)
            for remove in [key for key, val in kwargs.items() if key in (remove_kwargs or []) and val is None]:
                kwargs.pop(remove, None)
            api_response: ResultT = api_operation(api_instance, *args, **kwargs)
            return api_response
        return decorated_single_request
    return decorate


PageInfoResultT = Union[
    # FIXME list more paged types here
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


def repo_get_artifact_by_uuid(node: Node,
                              uuid: str,
                              namespace: str = _first(__RS, '$.paths["/artifacts/{uuid}"].get.parameters[?(@.name == "namespace")].schema.default'),
                              include_content: rs.IncludeContentEnum = _first(__RS, '$.components.schemas.includeContentEnum.default')) -> MultipartParser:
    @_single_request_template(Node.make_repo_conf,
                              rs.ApiClient,
                              rs.ArtifactsApi,
                              rs.ArtifactsApi.get_artifact_data_by_multipart)
    def _repo_get_artifact_by_uuid(node: Node,
                                   uuid: str,
                                   namespace: str = None,
                                   include_content: rs.IncludeContentEnum = None) -> str:
        pass
    result: str = _repo_get_artifact_by_uuid(node,
                                             uuid,
                                             namespace=namespace,
                                             include_content=include_content)
    # Result is of type str but seems to be a repr() string "b'...'"
    boundary = (byte_input := eval(result)).partition(b'\r\n')[0].partition(b'--')[2]
    return MultipartParser(BytesIO(byte_input), boundary)


def repo_get_artifact_response_by_uuid(node: Node,
                                       uuid: str,
                                       namespace: str = _first(__RS, '$.paths["/artifacts/{uuid}/response"].get.parameters[?(@.name == "namespace")].schema.default'),
                                       include_content: rs.IncludeContentEnum = _first(__RS, '$.components.schemas.includeContentEnum.default')) -> str:
    @_single_request_template(Node.make_repo_conf,
                              rs.ApiClient,
                              rs.ArtifactsApi,
                              rs.ArtifactsApi.get_artifact_data_by_response)
    def _repo_get_artifact_response_by_uuid(node: Node,
                                            uuid: str,
                                            namespace: str = None,
                                            include_content: rs.IncludeContentEnum = None) -> str:
        pass
    result: str = _repo_get_artifact_response_by_uuid(node,
                                                      uuid,
                                                      namespace=namespace,
                                                      include_content=include_content)
    # Result is of type str but seems to be a repr() string "b'...'"
    return eval(result).decode()


def repo_get_artifact_payload_by_uuid(node: Node,
                                      uuid: str,
                                      namespace: str = _first(__RS, '$.paths["/artifacts/{uuid}/payload"].get.parameters[?(@.name == "namespace")].schema.default'),
                                      include_content: rs.IncludeContentEnum = _first(__RS, '$.components.schemas.includeContentEnum.default')) -> bytes:
    @_single_request_template(Node.make_repo_conf,
                              rs.ApiClient,
                              rs.ArtifactsApi,
                              rs.ArtifactsApi.get_artifact_data_by_payload)
    def _repo_get_artifact_payload_by_uuid(node: Node,
                                           uuid: str,
                                           namespace: str = None) -> str:
        pass
    result: str = _repo_get_artifact_payload_by_uuid(node,
                                                     uuid, namespace=namespace,
                                                     include_content=include_content)
    # Result is of type str but seems to be a repr() string "b'...'"
    return eval(result)


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifacts,
                          remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_auid_page(node: Node,
                                    auid: str,
                                    url: Optional[str] = None,
                                    url_prefix: Optional[str] = None,
                                    namespace: str = _first(__RS, '$.paths["/aus/{auid}/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                    version: Optional[Union[int, rs.VersionsEnum]] = None,
                                    include_uncommitted: Optional[bool] = None,
                                    limit: Optional[int] = None,
                                    continuation_token: Optional[str] = None) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_auid_page)
def repo_get_artifacts_by_auid_page_iter(node: Node,
                                         auid: str,
                                         url: Optional[str] = None,
                                         url_prefix: Optional[str] = None,
                                         namespace: str = _first(__RS, '$.paths["/aus/{auid}/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                         version: Optional[Union[int, rs.VersionsEnum]] = None,
                                         include_uncommitted: Optional[bool] = None,
                                         limit: Optional[int] = None) -> Iterable[rs.ArtifactPageInfo]:
    pass


def repo_get_artifacts_by_auid(node: Node,
                               auid: str,
                               url: Optional[str] = None,
                               url_prefix: Optional[str] = None,
                               namespace: str = _first(__RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                               version: Optional[Union[int, rs.VersionsEnum]] = None,
                               include_uncommitted: Optional[bool] = None,
                               limit: Optional[int] = None) -> list[rs.Artifact]:
    ret = []
    for page in repo_get_artifacts_by_auid_page_iter(node,
                                                     auid,
                                                     url=url,
                                                     url_prefix=url_prefix,
                                                     namespace=namespace,
                                                     version=version,
                                                     include_uncommitted=include_uncommitted,
                                                     limit=limit):
        ret.extend(page.artifacts)
    return ret


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifacts_from_all_aus,
                          remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_url_page(node: Node,
                                   url: Optional[str] = None,
                                   url_prefix: Optional[str] = None,
                                   namespace: str = _first(__RS, '$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                   versions: rs.VersionsEnum = _first(__RS, '$.components.schemas.versionsEnum.default'),
                                   limit: Optional[int] = None,
                                   continuation_token: Optional[str] = None) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_url_page)
def repo_get_artifacts_by_url_page_iter(node: Node,
                                        url: Optional[str] = None,
                                        url_prefix: Optional[str] = None,
                                        namespace: str = _first(__RS, '$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                        versions: rs.VersionsEnum = _first(__RS, '$.components.schemas.versionsEnum.default'),
                                        limit: Optional[int] = None) -> Iterable[rs.ArtifactPageInfo]:
    pass


def repo_get_artifacts_by_url(node: Node,
                              url: Optional[str] = None,
                              url_prefix: Optional[str] = None,
                              namespace: str = _first(__RS, '$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                              versions: rs.VersionsEnum = _first(__RS, '$.components.schemas.versionsEnum.default'),
                              limit: Optional[int] = None) -> list[rs.Artifact]:
    ret = []
    for page in repo_get_artifacts_by_url_page_iter(node,
                                                    url=url,
                                                    url_prefix=url_prefix,
                                                    namespace=namespace,
                                                    versions=versions,
                                                    limit=limit):
        ret.extend(page.artifacts)
    return ret


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.AusApi,
                          rs.AusApi.get_artifacts_size)
def repo_get_au_size(node: Node,
                     auid: str,
                     namespace: str = _first(__RS, '$.paths["/aus/{auid}/size"].get.parameters[?(@.name == "namespace")].schema.default')) -> rs.AuSize:
    pass


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.AusApi,
                          rs.AusApi.get_aus)
def repo_get_auids_page(node: Node,
                        namespace: str = _first(__RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                        limit: Optional[int] = None,
                        continuation_token: Optional[str] = None) -> rs.AuidPageInfo:
    pass


@_paged_request_iterator_template(repo_get_auids_page)
def repo_get_auids_page_iter(node: Node,
                             namespace: str = _first(__RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                             limit: Optional[int] = None) -> Iterable[rs.AuidPageInfo]:
    pass


def repo_get_auids(node: Node,
                   namespace: str = _first(__RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                   limit: Optional[int] = None) -> list[str]:
    ret = []
    for page in repo_get_auids_page_iter(node,
                                         namespace=namespace,
                                         limit=limit):
        ret.extend(page.auids)
    return ret


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_supported_checksum_algorithms)
def repo_get_checksum_algorithms(node: Node) -> list[str]:
    pass


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_repository_information)
def repo_get_info(node: Node) -> rs.RepositoryInfo:
    pass


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_namespaces)
def repo_get_namespaces(node: Node) -> list[str]:
    pass


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.StatusApi,
                          rs.StatusApi.get_status,
                          needs_auth=False)
def repo_get_status(node: Node) -> rs.ApiStatus:
    pass


@_single_request_template(Node.make_repo_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_storage_info)
def repo_get_storage_info(node: Node) -> rs.StorageInfo:
    pass


if __name__ == '__main__':
    node = Node('localhost', 'lockss-u')
    print(repo_get_status(node).to_dict())
    print(repo_get_namespaces(node))
    print(repo_get_checksum_algorithms(node))
    print(repo_get_info(node))
    print(repo_get_auids(node))
    auid1 = 'org|lockss|plugin|RegistryPlugin&base_url~http%3A%2F%2Fprops%2Elockss%2Eorg%3A8001%2Fplugins%2Faserl-etd%2F'
    print(repo_get_au_size(node, auid1))
    print(repo_get_artifacts_by_auid(node, auid1))
    url1 = 'http://props.lockss.org:8001/plugins/aserl-etd/FSUETDPlugin.jar'
    print(repo_get_artifacts_by_url(node, url=url1))
    uuid1 = '4fa8b54e-9cfb-46ab-a0d6-ed3d0a2910f4'
    for part in repo_get_artifact_by_uuid(node, uuid1):
        print(part.name)
    print(repo_get_artifact_response_by_uuid(node, uuid1))
    print(repo_get_artifact_payload_by_uuid(node, uuid1))
