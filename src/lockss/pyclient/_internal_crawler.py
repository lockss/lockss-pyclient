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
Base of the lockss.pyclient package (crawler service).
"""

from collections.abc import Iterator
from typing import Optional

from ._internal_common import Node, _paged_request_iterator_template, _single_request_template
from . import crawler


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_by_id)
def crawler_get_crawl(node: Node,
                      job_id: str) -> crawler.CrawlStatus:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawls)
def crawler_get_crawls_page(node: Node,
                            limit: Optional[int] = None,
                            continuation_token: Optional[str] = None) -> crawler.CrawlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawls_page,
                                  lambda x: x.crawls)
def crawler_get_crawls(node: Node,
                       limit: Optional[int] = None) -> Iterator[crawler.CrawlStatus]:
    pass

@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_by_mime_type)
def crawler_get_crawl_by_type_page(node: Node,
                                   job_id: str,
                                   content_type: str,
                                   limit: Optional[int] = None,
                                   continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_by_type_page,
                                  lambda x: x.urls)
def crawler_get_crawl_by_type(node: Node,
                              job_id: str,
                              content_type: str,
                              limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_errors)
def crawler_get_crawl_errors_page(node: Node,
                                  job_id: str,
                                  limit: Optional[int] = None,
                                  continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_errors_page,
                                  lambda x: x.urls)
def crawler_get_crawl_errors(node: Node,
                             job_id: str,
                             limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_excluded)
def crawler_get_crawl_excluded_page(node: Node,
                                    job_id: str,
                                    limit: Optional[int] = None,
                                    continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_excluded_page,
                                  lambda x: x.urls)
def crawler_get_crawl_excluded(node: Node,
                               job_id: str,
                               limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_fetched)
def crawler_get_crawl_fetched_page(node: Node,
                                   job_id: str,
                                   limit: Optional[int] = None,
                                   continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_fetched_page,
                                  lambda x: x.urls)
def crawler_get_crawl_fetched(node: Node,
                              job_id: str,
                              limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_not_modified)
def crawler_get_crawl_not_modified_page(node: Node,
                                        job_id: str,
                                        limit: Optional[int] = None,
                                        continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_not_modified_page,
                                  lambda x: x.urls)
def crawler_get_crawl_not_modified(node: Node,
                                   job_id: str,
                                   limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_parsed)
def crawler_get_crawl_parsed_page(node: Node,
                                  job_id: str,
                                  limit: Optional[int] = None,
                                  continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_parsed_page,
                                  lambda x: x.urls)
def crawler_get_crawl_parsed(node: Node,
                             job_id: str,
                             limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlsApi,
                          crawler.CrawlsApi.get_crawl_pending)
def crawler_get_crawl_pending_page(node: Node,
                                   job_id: str,
                                   limit: Optional[int] = None,
                                   continuation_token: Optional[str] = None) -> crawler.UrlPager:
    pass


@_paged_request_iterator_template(crawler_get_crawl_pending_page,
                                  lambda x: x.urls)
def crawler_get_crawl_pending(node: Node,
                              job_id: str,
                              limit: Optional[int] = None) -> Iterator[crawler.UrlInfo]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlersApi,
                          crawler.CrawlersApi.get_crawler_config)
def crawler_get_crawler(node: Node,
                        crawler_id: str) -> crawler.CrawlerConfig:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.CrawlersApi,
                          crawler.CrawlersApi.get_crawlers)
def crawler_get_crawlers(node: Node) -> crawler.CrawlerStatuses:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.JobsApi,
                          crawler.JobsApi.get_crawl_job)
def crawler_get_job(node: Node,
                    job_id: str) -> crawler.CrawlJob:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.JobsApi,
                          crawler.JobsApi.get_jobs)
def crawler_get_jobs_page(node: Node,
                          limit: Optional[int] = None,
                          continuation_token: Optional[str] = None) -> crawler.JobPager:
    pass


@_paged_request_iterator_template(crawler_get_jobs_page,
                                  lambda x: x.jobs)
def crawler_get_jobs(node: Node,
                     limit: Optional[int] = None) -> Iterator[crawler.CrawlJob]:
    pass


@_single_request_template(Node.make_crawler_conf,
                          crawler.ApiClient,
                          crawler.StatusApi,
                          crawler.StatusApi.get_status,
                          needs_auth=False)
def crawler_get_status(node: Node) -> crawler.ApiStatus:
    pass
