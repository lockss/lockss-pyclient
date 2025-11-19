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
Base of the lockss.pyclient package (repository service).
"""

from collections.abc import Iterable
from io import BytesIO
from multipart import MultipartParser
from typing import Optional, Union

from .base import Node, _first, _single_request_template, _paged_request_iterator_template, _RS
from . import rs


def repo_get_artifact_by_uuid(node: Node,
                              uuid: str,
                              namespace: str = _first(_RS, '$.paths["/artifacts/{uuid}"].get.parameters[?(@.name == "namespace")].schema.default'),
                              include_content: rs.IncludeContentEnum = _first(_RS, '$.components.schemas.includeContentEnum.default')) -> MultipartParser:
    @_single_request_template(Node.make_rs_conf,
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
                                       namespace: str = _first(_RS, '$.paths["/artifacts/{uuid}/response"].get.parameters[?(@.name == "namespace")].schema.default'),
                                       include_content: rs.IncludeContentEnum = _first(_RS, '$.components.schemas.includeContentEnum.default')) -> str:
    @_single_request_template(Node.make_rs_conf,
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
                                      namespace: str = _first(_RS, '$.paths["/artifacts/{uuid}/payload"].get.parameters[?(@.name == "namespace")].schema.default'),
                                      include_content: rs.IncludeContentEnum = _first(_RS, '$.components.schemas.includeContentEnum.default')) -> bytes:
    @_single_request_template(Node.make_rs_conf,
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


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifacts,
                          remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_auid_page(node: Node,
                                    auid: str,
                                    url: Optional[str] = None,
                                    url_prefix: Optional[str] = None,
                                    namespace: str = _first(_RS, '$.paths["/aus/{auid}/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
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
                                         namespace: str = _first(_RS, '$.paths["/aus/{auid}/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                         version: Optional[Union[int, rs.VersionsEnum]] = None,
                                         include_uncommitted: Optional[bool] = None,
                                         limit: Optional[int] = None) -> Iterable[rs.ArtifactPageInfo]:
    pass


def repo_get_artifacts_by_auid(node: Node,
                               auid: str,
                               url: Optional[str] = None,
                               url_prefix: Optional[str] = None,
                               namespace: str = _first(_RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
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


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifacts_from_all_aus,
                          remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_url_page(node: Node,
                                   url: Optional[str] = None,
                                   url_prefix: Optional[str] = None,
                                   namespace: str = _first(_RS, '$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                   versions: rs.VersionsEnum = _first(_RS, '$.components.schemas.versionsEnum.default'),
                                   limit: Optional[int] = None,
                                   continuation_token: Optional[str] = None) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_url_page)
def repo_get_artifacts_by_url_page_iter(node: Node,
                                        url: Optional[str] = None,
                                        url_prefix: Optional[str] = None,
                                        namespace: str = _first(_RS, '$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                                        versions: rs.VersionsEnum = _first(_RS, '$.components.schemas.versionsEnum.default'),
                                        limit: Optional[int] = None) -> Iterable[rs.ArtifactPageInfo]:
    pass


def repo_get_artifacts_by_url(node: Node,
                              url: Optional[str] = None,
                              url_prefix: Optional[str] = None,
                              namespace: str = _first(_RS, '$.paths["/artifacts"].get.parameters[?(@.name == "namespace")].schema.default'),
                              versions: rs.VersionsEnum = _first(_RS, '$.components.schemas.versionsEnum.default'),
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


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.AusApi,
                          rs.AusApi.get_artifacts_size)
def repo_get_au_size(node: Node,
                     auid: str,
                     namespace: str = _first(_RS, '$.paths["/aus/{auid}/size"].get.parameters[?(@.name == "namespace")].schema.default')) -> rs.AuSize:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.AusApi,
                          rs.AusApi.get_aus)
def repo_get_auids_page(node: Node,
                        namespace: str = _first(_RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                        limit: Optional[int] = None,
                        continuation_token: Optional[str] = None) -> rs.AuidPageInfo:
    pass


@_paged_request_iterator_template(repo_get_auids_page)
def repo_get_auids_page_iter(node: Node,
                             namespace: str = _first(_RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                             limit: Optional[int] = None) -> Iterable[rs.AuidPageInfo]:
    pass


def repo_get_auids(node: Node,
                   namespace: str = _first(_RS, '$.paths["/aus"].get.parameters[?(@.name == "namespace")].schema.default'),
                   limit: Optional[int] = None) -> list[str]:
    ret = []
    for page in repo_get_auids_page_iter(node,
                                         namespace=namespace,
                                         limit=limit):
        ret.extend(page.auids)
    return ret


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_supported_checksum_algorithms)
def repo_get_checksum_algorithms(node: Node) -> list[str]:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_repository_information)
def repo_get_info(node: Node) -> rs.RepositoryInfo:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.RepoApi,
                          rs.RepoApi.get_namespaces)
def repo_get_namespaces(node: Node) -> list[str]:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.StatusApi,
                          rs.StatusApi.get_status,
                          needs_auth=False)
def repo_get_status(node: Node) -> rs.ApiStatus:
    pass


@_single_request_template(Node.make_rs_conf,
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
