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

from collections.abc import Callable
from concurrent.futures import Executor, Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from inspect import ismethod
from itertools import chain
from pathlib import Path
from typing import Any, Optional, TypeAlias

from click_extra import ExtraContext, Section, echo, group, pass_context, prompt
from click_plugins import with_plugins
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines
from lockss.pybasic.nodeutil import NodeSet, get_node_spec_adapter
from pydantic import ValidationError
import yaml

from . import rs, __copyright__, __license__, __version__
from ._core import LockssClient


YamlT: TypeAlias = Any


class _LockssApiCli(object):

    @dataclass(kw_only=True)
    class _Opts(object):
        """Data class to hold parsed command line options."""
        # Node options
        node_set: tuple[Path, ...] = ()
        node_spec: tuple[str, ...] = ()
        node_specs: tuple[Path, ...] = ()
        username: Optional[str] = None
        password: Optional[str] = field(default=None, repr=False)

    def __init__(self, ctx: ExtraContext) -> None:
        """
        Constructor.

        :param ctx: The Click Extra context.
        :type ctx: ExtraContext
        """
        super().__init__()
        self._ctx: ExtraContext = ctx
        self._opts: Optional[_LockssApiCli._Opts] = None
        self._clients: list[LockssClient] = list()
        self._executor: Optional[Executor] = None

    def dispatch(self, method: Callable[[], None], **cli_kwargs) -> None:
        """
        Initializes from the given command line options and invokes the given
        (bound) method.

        :param method: A (bound) method.
        :type method: Callable[[], None]
        :param cli_kwargs: The command line arguments passed by Click Extra.
        :type cli_kwargs: dict[str, Any]
        """
        if not ismethod(method):
            raise InternalError from ValueError(method)
        self._opts = _LockssApiCli._Opts(**cli_kwargs)
        method()

    #
    # REPOSITORY
    #

    def get_repository_service_status(self) -> None:
        pass

    #
    # PROTECTED
    #

    def _initialize_clients(self) -> None:
        """
        Initializes clients.
        """
        # First, process the nodes...
        clients: list[LockssClient] = list()
        # ...first from node sets
        for node_set_path in (opts := self._opts).node_set:
            with node_set_path.open('r') as node_set_input:
                try:
                    node_set_yaml: YamlT = yaml.safe_load(node_set_input)
                    node_set: NodeSet = NodeSet.model_validate(node_set_yaml)
                    for node_spec in node_set.nodes:
                        clients.append(LockssClient(node_spec))
                except (yaml.YAMLError, ValidationError) as exc:
                    self._ctx.fail(str(exc))
        # ...then from compact node specifications
        for compact_node_spec in [*opts.node_spec, *chain.from_iterable(file_lines(file_path) for file_path in opts.node_specs)]:
            try:
                clients.append(LockssClient(get_node_spec_adapter().validate_python(compact_node_spec)))
            except ValidationError as exc:
                self._ctx.fail(str(exc))
        if len(clients) == 0:
            self._ctx.fail('The list of nodes to process is empty')
        # Then, initialize the thread pool
        self._executor = ThreadPoolExecutor(max_workers=opts.jobs)
        # Finally, authenticate
        u, opts.username = opts.username if opts.username else prompt('UI username'), None
        p, opts.password = opts.password if opts.password else prompt('UI password', hide_input=True), None
        for client in clients:
            client.authenticate(u, p)
        self._clients.extend(clients)

@with_plugins(entry_points(module='click_command_tree')) # adds a 'tree' command
@group(params=None)
@pass_context
def lockssapi(ctx: ExtraContext, **kwargs):
    ctx.obj = _LockssApiCli(ctx)


@lockssapi.command(help='Show the copyright and exit.')
def copyright() -> None:
    """Show the copyright and exit"""
    echo(__copyright__)


@lockssapi.command(help='Show the software license and exit.')
def license() -> None:
    """Show the software license and exit"""
    echo(__license__)


# 'tree' command implied by click_command_tree plugin


@lockssapi.command(help='Show the version number and exit.')
def version() -> None:
    """Show the version number and exit"""
    echo(__version__)


#
# REPOSITORY
#

_REPOSITORY_COMMANDS = Section('Repository commands')


@lockssapi.command(help='Get the status of the LOCKSS Repository Service.')
def get_repository_service_status(cli: _LockssApiCli, **kwargs) -> None:
    """Get the status of the LOCKSS Repository Service"""
    cli.dispatch(cli.get_repository_service_status, **kwargs)


def main() -> None:
    """
    Entry point for the lockssapi2 command line tool.
    """
    lockssapi()
