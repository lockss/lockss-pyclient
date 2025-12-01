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
Base of the lockss.pyclient package (metadata service).
"""

from collections.abc import Iterable
from typing import Optional

from ._internal_common import Node, _paged_request_iterator_template, _single_request_template
from . import md


@_single_request_template(Node.make_md_conf,
                          md.ApiClient,
                          md.UrlsApi,
                          md.UrlsApi.get_urls_doi)
def md_doi_query(node: Node,
                 doi: str) -> md.UrlInfo:
    pass


@_single_request_template(Node.make_md_conf,
                          md.ApiClient,
                          md.MdupdatesApi,
                          md.MdupdatesApi.get_mdupdates_jobid)
def md_get_job(node: Node,
               jobid: str) -> md.Status:
    pass


@_single_request_template(Node.make_md_conf,
                          md.ApiClient,
                          md.MdupdatesApi,
                          md.MdupdatesApi.get_mdupdates)
def md_get_jobs_page(node: Node,
                     limit: Optional[int] = None,
                     continuation_token: Optional[str] = None) -> md.JobPageInfo:
    pass


@_paged_request_iterator_template(md_get_jobs_page)
def md_get_jobs_iter(node: Node,
                     limit: Optional[int] = None) -> Iterable[md.JobPageInfo]:
    pass


def md_get_jobs(node: Node,
                limit: Optional[int] = None) -> list[md.JobPageInfo]:
    ret: list[md.JobPageInfo] = []
    for page in md_get_jobs_iter(node,
                                 limit=limit):
        ret.extend(page.jobs)
    return ret


@_single_request_template(Node.make_md_conf,
                          md.ApiClient,
                          md.MetadataApi,
                          md.MetadataApi.get_metadata_aus_auid)
def md_get_metadata_page(node: Node,
                         auid: str,
                         limit: Optional[int] = None,
                         continuation_token: Optional[str] = None) -> md.AuMetadataPageInfo:
    pass


@_paged_request_iterator_template(md_get_metadata_page)
def md_get_metadata_iter(node: Node,
                         auid: str,
                         limit: Optional[int] = None) -> Iterable[md.AuMetadataPageInfo]:
    pass


def md_get_metadata(node: Node,
                    auid: str,
                    limit: Optional[int] = None) -> list[md.ItemMetadata]:
    ret: list[md.ItemMetadata] = []
    for page in md_get_metadata_iter(node,
                                     auid,
                                     limit=limit):
        ret.extend(page.items)
    return ret


@_single_request_template(Node.make_md_conf,
                          md.ApiClient,
                          md.StatusApi,
                          md.StatusApi.get_status,
                          needs_auth=False)
def md_get_status(node: Node) -> md.ApiStatus:
    pass


@_single_request_template(Node.make_md_conf,
                          md.ApiClient,
                          md.UrlsApi,
                          md.UrlsApi.get_urls_open_url)
def md_openurl_query(node: Node,
                     params: list[str]) -> md.UrlInfo:
    pass
