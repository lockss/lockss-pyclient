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
Base of the lockss.pyclient package (poller service).
"""

from collections.abc import Iterable
from typing import Optional

from .base import Node, _single_request_template, _paged_request_iterator_template
from . import poller


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.PollDetailApi,
                          poller.PollDetailApi.get_poll_peer_vote_urls)
def poller_get_peer_data_page(node: Node,
                              poll_key: str,
                              peer_id: str,
                              url_type: poller.VoterUrlsEnum,
                              limit: Optional[int] = None,
                              continuation_token: Optional[str] = None) -> poller.UrlPageInfo:
    pass


@_paged_request_iterator_template(poller_get_peer_data_page)
def poller_get_peer_data_iter(node: Node,
                              poll_key: str,
                              peer_id: str,
                              url_type: poller.VoterUrlsEnum,
                              limit: Optional[int] = None) -> Iterable[poller.UrlPageInfo]:
    pass


def poller_get_peer_data(node: Node,
                         poll_key: str,
                         peer_id: str,
                         url_type: poller.VoterUrlsEnum,
                         limit: Optional[int] = None) -> list[str]:
    ret: list[str] = []
    for page in poller_get_peer_data_iter(node,
                                          poll_key,
                                          peer_id,
                                          url_type,
                                          limit=limit):
        ret.extend(page.urls)
    return ret


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.ServiceApi,
                          poller.ServiceApi.get_poll_status)
def poller_get_poll_status(node: Node,
                           job_id: str) -> poller.PollerSummary:
    pass


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.PollerPollsApi,
                          poller.PollerPollsApi.get_poller_poll_details)
def poller_get_poller_poll(node: Node,
                           poll_key: str) -> poller.PollerDetail:
    pass


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.PollerPollsApi,
                          poller.PollerPollsApi.get_polls_as_poller)
def poller_get_poller_polls_page(node: Node,
                                 limit: Optional[int] = None,
                                 continuation_token: Optional[str] = None) -> poller.PollerPageInfo:
    pass


@_paged_request_iterator_template(poller_get_poller_polls_page)
def poller_get_poller_polls_iter(node: Node,
                                 limit: Optional[int] = None) -> Iterable[poller.PollerPageInfo]:
    pass


def poller_get_poller_polls(node: Node,
                                 limit: Optional[int] = None) -> list[poller.PollerSummary]:
    ret: list[poller.PollerSummary] = []
    for page in poller_get_poller_polls_iter(node,
                                             limit=limit):
        ret.extend(page.polls)
    return ret


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.PollDetailApi,
                          poller.PollDetailApi.get_repair_queue_data)
def poller_get_repair_data_page(node: Node,
                                poll_key: str,
                                repair_type: poller.RepairTypeEnum,
                                limit: Optional[int] = None,
                                continuation_token: Optional[str] = None) -> poller.RepairPageInfo:
    pass


@_paged_request_iterator_template(poller_get_repair_data_page)
def poller_get_repair_data_iter(node: Node,
                                poll_key: str,
                                repair_type: poller.RepairTypeEnum,
                                limit: Optional[int] = None) -> Iterable[poller.RepairPageInfo]:
    pass


def poller_get_repair_data(node: Node,
                           poll_key: str,
                           repair_type: poller.RepairTypeEnum,
                           limit: Optional[int] = None) -> list[poller.RepairData]:
    ret: list[poller.RepairData] = []
    for page in poller_get_repair_data_iter(node,
                                            poll_key,
                                            repair_type,
                                            limit=limit):
        ret.extend(page.repairs)
    return ret


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.ServiceApi,
                          poller.ServiceApi.get_status,
                          needs_auth=False)
def poller_get_status(node: Node) -> poller.ApiStatus:
    pass


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.PollDetailApi,
                          poller.PollDetailApi.get_tally_urls)
def poller_get_tally_urls_page(node: Node,
                               poll_key: str,
                               tally_type: poller.TallyTypeEnum,
                               limit: Optional[int] = None,
                               continuation_token: Optional[str] = None) -> poller.UrlPageInfo:
    pass


@_paged_request_iterator_template(poller_get_tally_urls_page)
def poller_get_tally_urls_iter(node: Node,
                               poll_key: str,
                               tally_type: poller.TallyTypeEnum,
                               limit: Optional[int] = None) -> Iterable[poller.UrlPageInfo]:
    pass


def poller_get_tally_urls(node: Node,
                          poll_key: str,
                          tally_type: poller.TallyTypeEnum,
                          limit: Optional[int] = None) -> list[str]:
    ret: list[str] = []
    for page in poller_get_tally_urls_iter(node,
                                           poll_key,
                                           tally_type,
                                           limit=limit):
        ret.extend(page.urls)
    return ret


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.VoterPollsApi,
                          poller.VoterPollsApi.get_voter_poll_details)
def poller_get_voter_poll(node: Node,
                          poll_key: str) -> poller.VoterDetail:
    pass


@_single_request_template(Node.make_poller_conf,
                          poller.ApiClient,
                          poller.VoterPollsApi,
                          poller.VoterPollsApi.get_polls_as_voter)
def poller_get_voter_polls_page(node: Node,
                                limit: Optional[int] = None,
                                continuation_token: Optional[str] = None) -> poller.PollerPageInfo:
    pass


@_paged_request_iterator_template(poller_get_voter_polls_page)
def poller_get_voter_polls_iter(node: Node,
                                limit: Optional[int] = None) -> Iterable[poller.PollerPageInfo]:
    pass


def poller_get_voter_polls(node: Node,
                           limit: Optional[int] = None) -> list[poller.PollerSummary]:
    ret: list[poller.PollerSummary] = []
    for page in poller_get_voter_polls_iter(node,
                                            limit=limit):
        ret.extend(page.polls)
    return ret
