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

from collections.abc import Iterator
from typing import Optional, Union

from multipart import MultipartParser

from ._internal_common import Node, bytes_repr_to_multipart, bytes_repr_to_string, _param_default, _schema_default, _single_request_template, _paged_request_iterator_template, _RS
from . import rs


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.delete_artifact)
def repo_delete_artifact(node: Node,
                         uuid: str,
                         namespace: str = _param_default(_RS, '/artifacts/{uuid}', 'delete', 'namespace')) -> None:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifact_data_by_multipart,
                          transform_result=bytes_repr_to_multipart)
def repo_get_artifact_by_uuid(node: Node,
                              uuid: str,
                              namespace: str = _param_default(_RS, '/artifacts/{uuid}', 'get', 'namespace'),
                              include_content: rs.IncludeContentEnum = _schema_default(_RS, 'includeContentEnum')) -> MultipartParser:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifact_data_by_response,
                          transform_result=bytes_repr_to_string)
def repo_get_artifact_response_by_uuid(node: Node,
                                       uuid: str,
                                       namespace: str = _param_default(_RS, '/artifacts/{uuid}/response', 'get', 'namespace'),
                                       include_content: rs.IncludeContentEnum = _schema_default(_RS, 'includeContentEnum')) -> str:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifact_data_by_payload,
                          transform_result=eval)
def repo_get_artifact_payload_by_uuid(node: Node,
                                      uuid: str,
                                      namespace: str = _param_default(_RS, '/artifacts/{uuid}/payload', 'get', 'namespace'),
                                      include_content: rs.IncludeContentEnum = _schema_default(_RS, 'includeContentEnum')) -> bytes:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifacts,
                          remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_auid_page(node: Node,
                                    auid: str,
                                    url: Optional[str] = None,
                                    url_prefix: Optional[str] = None,
                                    namespace: str = _param_default(_RS, '/aus/{auid}/artifacts', 'get', 'namespace'),
                                    versions: Optional[Union[int, rs.VersionsEnum]] = None,
                                    include_uncommitted: Optional[bool] = None,
                                    limit: Optional[int] = None,
                                    continuation_token: Optional[str] = None) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_auid_page,
                                  lambda x: x.artifacts)
def repo_get_artifacts_by_auid(node: Node,
                               auid: str,
                               url: Optional[str] = None,
                               url_prefix: Optional[str] = None,
                               namespace: str = _param_default(_RS, '/aus/{auid}/artifacts', 'get', 'namespace'),
                               versions: Optional[Union[int, rs.VersionsEnum]] = None,
                               include_uncommitted: Optional[bool] = None,
                               limit: Optional[int] = None) -> Iterator[rs.Artifact]:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.ArtifactsApi,
                          rs.ArtifactsApi.get_artifacts_from_all_aus,
                          remove_kwargs=['url', 'url_prefix'])
def repo_get_artifacts_by_url_page(node: Node,
                                   url: Optional[str] = None,
                                   url_prefix: Optional[str] = None,
                                   namespace: str = _param_default(_RS, '/artifacts', 'get', 'namespace'),
                                   versions: rs.VersionsEnum = _schema_default(_RS, 'versionsEnum'),
                                   limit: Optional[int] = None,
                                   continuation_token: Optional[str] = None) -> rs.ArtifactPageInfo:
    pass


@_paged_request_iterator_template(repo_get_artifacts_by_url_page,
                                  lambda x: x.artifacts)
def repo_get_artifacts_by_url(node: Node,
                              url: Optional[str] = None,
                              url_prefix: Optional[str] = None,
                              namespace: str = _param_default(_RS, '/artifacts', 'get', 'namespace'),
                              versions: rs.VersionsEnum = _schema_default(_RS, 'versionsEnum'),
                              limit: Optional[int] = None) -> Iterator[rs.Artifact]:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.AusApi,
                          rs.AusApi.get_artifacts_size)
def repo_get_au_size(node: Node,
                     auid: str,
                     namespace: str = _param_default(_RS, '/aus/{auid}/size', 'get', 'namespace')) -> rs.AuSize:
    pass


@_single_request_template(Node.make_rs_conf,
                          rs.ApiClient,
                          rs.AusApi,
                          rs.AusApi.get_aus)
def repo_get_auids_page(node: Node,
                        namespace: str = _param_default(_RS, '/aus', 'get', 'namespace'),
                        limit: Optional[int] = None,
                        continuation_token: Optional[str] = None) -> rs.AuidPageInfo:
    pass


@_paged_request_iterator_template(repo_get_auids_page,
                                  lambda x: x.auids)
def repo_get_auids(node: Node,
                   namespace: str = _param_default(_RS, '/aus', 'get', 'namespace'),
                   limit: Optional[int] = None) -> Iterator[str]:
    pass


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


def repo_update_artifact(node: Node,
                         uuid: str,
                         committed: bool,
                         namespace: str = _param_default(_RS, '/artifacts/{uuid}', 'put', 'namespace')) -> rs.Artifact:
    @_single_request_template(Node.make_rs_conf,
                              rs.ApiClient,
                              rs.ArtifactsApi,
                              rs.ArtifactsApi.update_artifact)
    def _repo_update_artifact(node: Node,
                              committed: bool,
                              uuid: str,
                              namespace: str = _param_default(_RS, '/artifacts/{uuid}', 'put', 'namespace')) -> rs.Artifact:
        pass
    return _repo_update_artifact(node,
                                 committed,
                                 uuid,
                                 namespace=namespace)
