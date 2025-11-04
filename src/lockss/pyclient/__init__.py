#!/usr/bin/env python3

"""
LOCKSS Python clients
"""

# Remove in Python 3.14; see https://stackoverflow.com/a/33533514
from __future__ import annotations

__version__ = '0.1.0-dev2'

__copyright__ = '''
Copyright (c) 2000-2025, Board of Trustees of Leland Stanford Jr. University
'''.strip()

__license__ = __copyright__ + '\n\n' + '''
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''.strip()

from collections.abc import Callable, Iterable
from getpass import getpass
from importlib import resources
from io import BytesIO
from jsonpath import query
from multipart import MultipartParser
from typing import Any, ClassVar, Optional, TypeVar
import yaml

from lockss.pyclient import rs


YamlT = Any


def _load_swagger(package) -> YamlT:
    with resources.path(package, 'swagger.yaml') as p:
        with p.open('rb') as f:
            return yaml.safe_load(f)


__RS_SWAGGER = _load_swagger(rs)


def _first(json_path: str, data: YamlT) -> Any:
    return query(json_path, data).first_one().value


RS_DEFAULT_PORT: int = _first('$.servers[0].variables.port.default', __RS_SWAGGER)


ConfT = TypeVar('ConfT')


ConfProducer = Callable[[], ConfT]


StrProducer = Callable[[], str]


class Node(object):

    DEFAULT_PROTOCOL: ClassVar[str] = 'http'

    # Decorator
    @staticmethod
    def _make_conf_template(make_conf: ConfProducer,
                            get_port_name: str):
        def wrap(f):
            def decorated(self, needs_auth: bool = True):
                conf = make_conf()
                conf.host = f'{self.get_host()}:{getattr(self, get_port_name)()}'
                if needs_auth:
                    conf.username = self.get_username()
                    conf.password = self.get_password()()
                return conf
            return decorated
        return wrap

    # Decorator
    @staticmethod
    def _set_port_template(port_name: str):
        def wrap(f):
            def decorated(self, port: int) -> Node:
                setattr(self, port_name, port)
                return self
            return decorated
        return wrap

    # Decorator
    @staticmethod
    def _get_port_template(port_name: str,
                           default_port: int):
        def wrap(f):
            def decorated(self) -> int:
                return getattr(self, port_name, default_port)
            return decorated
        return wrap

    def __init__(self,
                 node_reference: str,
                 username: Optional[str] = None,
                 password: Optional[StrProducer] = None,
                 interactive: bool = True,
                 rs_port: int = RS_DEFAULT_PORT):
        super().__init__()
        self._host: str = Node._compute_host(node_reference)
        self._username: Optional[str] = username
        self._password: Optional[StrProducer] = password
        self._interactive: bool = interactive
        self._rs_port: int = rs_port

    def get_host(self) -> str:
        return self._host

    @_get_port_template('_rs_port', RS_DEFAULT_PORT)
    def get_rs_port(self) -> int:
        pass

    def get_username(self) -> str:
        return self._username

    def get_password(self) -> Optional[StrProducer]:
        if not self._password:
            if not self._interactive:
                raise RuntimeError('interactive prompts not allowed')
            _p = getpass(f'Password ({self.get_host().partition("://")[2]}): ')
            self._password = lambda: _p
        return self._password

    @_make_conf_template(rs.Configuration, 'get_rs_port')
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


ApiClientT = TypeVar('ApiClientT')


ApiClientProducer = Callable[..., ApiClientT]


ApiInstanceT = TypeVar('ApiInstanceT')


ApiInstanceProducer = Callable[[ApiClientT], ApiInstanceT]


ResultT = TypeVar('ResultT')


def _single_request_template(make_conf_name: str,
                             make_api_client: ApiClientProducer,
                             make_api_instance: ApiInstanceProducer,
                             api_operation_name: str,
                             needs_auth: bool = True,
                             remove_kwargs: Optional[list[str]] = None):
    def wrap(f):
        def decorated(node: Node, *args, **kwargs) -> ResultT:
            if needs_auth:
                repo_conf = getattr(node, make_conf_name)()
                api_client = make_api_client(repo_conf, "Authorization", repo_conf.get_basic_auth_token())
            else:
                repo_conf = getattr(node, make_conf_name)(needs_auth=False)
                api_client = make_api_client(repo_conf)
            api_instance = make_api_instance(api_client)
            if remove_kwargs:
                for key, val in kwargs.items():
                    if val is None:
                        kwargs.pop(key, None)
            api_response: ResultT = getattr(api_instance, api_operation_name)(*args, **kwargs)
            return api_response
        return decorated
    return wrap


PageInfoResultT = TypeVar('PageInfoResultT')


PageInfoResultProducer = Callable[..., PageInfoResultT]


def _paged_request_iterator_template(single_request: PageInfoResultProducer,
                                     remove_kwargs: Optional[list[str]] = None):
    def wrap(f):
        def decorated(*args, **kwargs) -> Iterable[PageInfoResultT]:
            if remove_kwargs:
                for arg, val in kwargs.items():
                    if val is None:
                        kwargs.pop(arg, None)
            token = None
            while True:
                if token:
                    kwargs['continuation_token'] = token
                else:
                    kwargs.pop('continuation_token', None)
                if 'limit' not in kwargs:
                    kwargs['limit'] = 100
                kwargs.pop('url_prefix', None) ### FIXME !!!
                result: PageInfoResultT = single_request(*args, **kwargs)
                token = result.page_info.continuation_token
                yield result
                if token is None:
                    break
        return decorated
    return wrap


def repo_get_artifact_by_uuid(node: Node,
                              uuid: str,
                              namespace: str = _first('$.paths["/artifacts/{uuid}"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> MultipartParser:
    @_single_request_template('make_repo_conf', rs.ApiClient, rs.ArtifactsApi, 'get_artifact_data_by_multipart')
    def _repo_get_artifact_by_uuid(node: Node, uuid: str, namespace: str = None) -> str:
        pass
    result: str = _repo_get_artifact_by_uuid(node, uuid, namespace=namespace)
    # Result is of type str but seems to be a repr() string!
    byte_input = eval(result)
    boundary = byte_input.partition(b'\r\n')[0].partition(b'--')[2]
    return MultipartParser(BytesIO(byte_input), boundary)


@_single_request_template('make_repo_conf', rs.ApiClient, rs.ArtifactsApi, 'get_artifacts')
def repo_get_artifacts_by_auid_page(node: Node,
                                    auid: str,
                                    namespace: str = _first('$.paths["/aus/{auid}/artifacts"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_auid_page)
def repo_get_artifacts_by_auid_page_iter(node: Node,
                                         auid: str,
                                         namespace: str = _first('$.paths["/aus/{auid}/artifacts"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> Iterable[rs.ArtifactPageInfo]:
    pass


def repo_get_artifacts_by_auid(node: Node,
                               auid: str,
                               namespace: str = _first('$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> list[rs.Artifact]:
    ret = []
    for page in repo_get_artifacts_by_auid_page_iter(node, auid, namespace=namespace):
        ret.extend(page.artifacts)
    return ret


@_single_request_template('make_repo_conf', rs.ApiClient, rs.ArtifactsApi, 'get_artifacts_from_all_aus', remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_url_page(node: Node,
                                   url: Optional[str] = None,
                                   url_prefix: Optional[str] = None,
                                   namespace: Optional[str] = _first('$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_url_page)
def repo_get_artifacts_by_url_page_iter(node: Node,
                                        url: Optional[str] = None,
                                        url_prefix: Optional[str] = None,
                                        namespace: Optional[str] = _first('$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> Iterable[rs.ArtifactPageInfo]:
    pass


def repo_get_artifacts_by_url(node: Node,
                              url: Optional[str] = None,
                              url_prefix: Optional[str] = None,
                              namespace: Optional[str] = _first('$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> list[rs.Artifact]:
    ret = []
    for page in repo_get_artifacts_by_url_page_iter(node, url=url, url_prefix=url_prefix, namespace=namespace):
        ret.extend(page.artifacts)
    return ret


@_single_request_template('make_repo_conf', rs.ApiClient, rs.AusApi, 'get_artifacts_size')
def repo_get_au_size(node: Node,
                     auid: str,
                     namespace: Optional[str] = _first('$.paths["/aus/{auid}/size"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> rs.AuSize:
    pass


@_single_request_template('make_repo_conf', rs.ApiClient, rs.AusApi, 'get_aus')
def repo_get_auids_page(node: Node,
                        namespace: Optional[str] = _first('$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER),
                        **kwargs) -> rs.AuidPageInfo:
    pass


@_paged_request_iterator_template(repo_get_auids_page)
def repo_get_auids_page_iter(node: Node,
                             namespace: Optional[str] = _first('$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> Iterable[rs.AuidPageInfo]:
    pass


def repo_get_auids(node: Node,
                   namespace: Optional[str] = _first('$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default', __RS_SWAGGER)) -> list[str]:
    ret = []
    for page in repo_get_auids_page_iter(node, namespace=namespace):
        ret.extend(page.auids)
    return ret


@_single_request_template('make_repo_conf', rs.ApiClient, rs.RepoApi, 'get_supported_checksum_algorithms')
def repo_get_checksum_algorithms(node: Node) -> list[str]:
    pass


@_single_request_template('make_repo_conf', rs.ApiClient, rs.RepoApi, 'get_repository_information')
def repo_get_info(node: Node) -> rs.RepositoryInfo:
    pass


@_single_request_template('make_repo_conf', rs.ApiClient, rs.RepoApi, 'get_namespaces')
def repo_get_namespaces(node: Node) -> list[str]:
    pass


@_single_request_template('make_repo_conf', rs.ApiClient, rs.StatusApi, 'get_status', needs_auth=False)
def repo_get_status(node: Node) -> rs.ApiStatus:
    pass


# if __name__ == '__main__':
#     node = Node('localhost', 'lockss-u')
#     print(repo_status(node).to_dict())
#     print(repo_namespaces(node))
#     print(repo_checksum_algorithms(node))
#     print(repo_info(node))
#     print(repo_auids(node))
#     auid1 = 'org|lockss|plugin|RegistryPlugin&base_url~http%3A%2F%2Fprops%2Elockss%2Eorg%3A8001%2Fplugins%2Faserl-etd%2F'
#     print(repo_au_size(node, auid1))
#     print(repo_artifacts_by_auid(node, auid1))
#     url1 = 'http://props.lockss.org:8001/plugins/aserl-etd/FSUETDPlugin.jar'
#     print(repo_artifacts_by_url(node, url=url1))
#     uuid1 = '4fa8b54e-9cfb-46ab-a0d6-ed3d0a2910f4'
#     for part in repo_artifact_by_uuid(node, uuid1):
#         print(part.name)
