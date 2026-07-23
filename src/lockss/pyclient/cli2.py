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
Command line tool to interact with LOCKSS 1.x or 2.x via client interfaces.
"""

from collections.abc import Callable, Iterator
from concurrent.futures import Executor, Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from inspect import ismethod
from itertools import chain
from pathlib import Path
from typing import Any, Optional, TypeAlias

from click_extra import Context, Section, ProgressOption, TableFormat, accessible_option, color_option, echo, group, jobs_option, no_color_option, option, option_group, pass_context, pass_obj, print_data, prompt, progressbar, show_params_option, timer_option, tree_option
from click_extra.decorators import decorator_factory
from lockss.pybasic.cliutil import click_path
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines
from lockss.pybasic.nodeutil import NodeIdentifier, NodeSet, get_node_spec_adapter
from pydantic import ValidationError
import yaml

from . import rs, __copyright__, __license__, __version__
from ._core import LockssClient
from .output import sort_by_option


YamlT: TypeAlias = Any


progress_option = decorator_factory(dec=option, cls=ProgressOption)


class _LockssCli(object):

    @dataclass(kw_only=True)
    class _Opts(object):
        """Data class to hold parsed command line options."""
        # Node options
        node_set: tuple[Path, ...] = ()
        node_spec: tuple[str, ...] = ()
        node_specs: tuple[Path, ...] = ()
        username: Optional[str] = None
        password: Optional[str] = field(default=None, repr=False)
        # Job options
        jobs: Optional[int] = None
        # Display options
        accessible: Optional[bool] = None
        color: Optional[bool] = None
        progress: Optional[bool] = None
        theme: Optional[str] = None
        time: Optional[bool] = None

    _ctx: Context
    _opts: _LockssCli._Opts
    _clients: list[LockssClient]

    def __init__(self, ctx: Context, **cli_kwargs) -> None:
        """
        Constructor.

        :param ctx: The Click Extra context.
        :type ctx: ExtraContext
        """
        super().__init__()
        self._ctx = ctx
        self._opts = _LockssCli._Opts(**cli_kwargs)

    #
    # REPOSITORY
    #

    def get_repository_service_status(self, **kwargs) -> None:
        self._initialize_clients()
        for client in self._clients:
            res = client.get_repository_service_status()
            print(client.get_id())
            print_data(res.to_dict(), TableFormat.YAML)

        # futures: dict[Future[rs.ApiStatus], LockssClient] = {self._executor.submit(LockssClient.get_repository_service_status, client, **kwargs): client for client in self._clients}
        # completed: Iterator[Future[rs.ApiStatus]] = as_completed(futures)
        # results: dict[NodeIdentifier, rs.ApiStatus] = {}
        # with progressbar(completed, length=len(futures), label='Progress') if opts.progress else nullcontext(completed) as bar:
        #     for future in bar:
        #         client: LockssClient = futures[future]
        #         k: NodeIdentifier = client.get_id()
        #         try:
        #             result: rs.ApiStatus = future.result()
        #             results[k] = result
        #         except Exception as exc:
        #             results[k] = exc

    #
    # PROTECTED
    #

    def _initialize_clients(self) -> None:
        """
        Initializes the list of clients. Fails if the list of nodes ends up
        being empty.
        """
        clients: list[LockssClient] = list()
        # First from node sets
        for node_set_path in (opts := self._opts).node_set:
            with node_set_path.open('r') as node_set_input:
                try:
                    node_set_yaml: YamlT = yaml.safe_load(node_set_input)
                    node_set: NodeSet = NodeSet.model_validate(node_set_yaml)
                    for node_spec in node_set.nodes:
                        clients.append(LockssClient(node_spec))
                except (yaml.YAMLError, ValidationError) as exc:
                    self._ctx.fail(str(exc))
        # Then from compact node specifications
        for compact_node_spec in [*opts.node_spec, *chain.from_iterable(file_lines(file_path) for file_path in opts.node_specs)]:
            try:
                clients.append(LockssClient(get_node_spec_adapter().validate_python(compact_node_spec)))
            except ValidationError as exc:
                self._ctx.fail(str(exc))
        # Fail if empty
        if len(clients) == 0:
            self._ctx.fail('The list of nodes to process is empty')
        self._clients = clients



#
# OPTIONS AND OPTION GROUPS
#

#: The node option group: --node-set/-s, --node-spec/-n, --node-specs/-N, --username/-U, --password/-P
_node_option_group = option_group(
    'Node options',
    option('--node-set', '-s', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the nodes from the node set in FILE to the list of nodes to process.'),
    option('--node-spec', '--node', '-n', metavar='NODE', multiple=True, help='Add the compact node specification NODE to the list of nodes to process.'),
    option('--node-specs', '--nodes', '-N', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the compact node specifications in FILE to the list of nodes to process.'),
    option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.'),
    option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.'),
)


#: The job option group: --jobs
_job_option_group = option_group(
    'Job options',
    jobs_option,
)


#: The display option group: --accessible, --color, --no-color, --progress/--no-progress
_display_option_group = option_group(
    'Display options',
    accessible_option,
    color_option,
    no_color_option,
    progress_option,
)


#: The debug option group: --show-params, --time/--no-time
_debug_option_group = option_group(
    'Debug options',
    show_params_option,
    timer_option
)


#
# CLICK INFRASTRUCTURE
#

@group(params=None)
@tree_option
@pass_context
def locksscli(ctx: Context, **kwargs):
    pass


@locksscli.command(help='Show the copyright and exit.')
def copyright(**kwargs) -> None:
    echo(__copyright__)


@locksscli.command(help='Show the software license and exit.')
def license(**kwargs) -> None:
    echo(__license__)


@locksscli.command(help='Show the version number and exit.')
def version(**kwargs) -> None:
    echo(__version__)


#
# REPOSITORY
#

_REPOSITORY_COMMANDS = Section('Repository commands')


@locksscli.command(section=_REPOSITORY_COMMANDS, help='Get the status of the LOCKSS Repository Service.')
@_node_option_group
@_display_option_group
@pass_obj
def get_repository_service_status(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_repository_service_status()


def main() -> None:
    """Entry point for the locksscli command line tool."""
    locksscli()
