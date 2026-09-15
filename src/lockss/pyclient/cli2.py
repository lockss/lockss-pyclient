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

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import cache
from itertools import chain
from pathlib import Path
from typing import Any, Concatenate, Optional, TypeAlias, TypeVar, Union

from click_extra import ColumnSpec, Context, OperationTrail, Section, ProgressOption, accessible_option, color_option, columns_option, echo, group, jobs_option, no_color_option, option, option_group, pass_context, print_table, prompt, run_jobs, select_columns, select_row, show_params_option, sort_by_option, table_format_option, timer_option, tree_option
from click_extra.context import COLUMNS, JOBS, PROGRESS, TABLE_FORMAT
from click_extra.decorators import decorator_factory
from click_extra.theme import KO_GLYPH, OK_GLYPH
from lockss.pybasic.cliutil import click_path, compose_decorators
from lockss.pybasic.errorutil import InternalError
from lockss.pybasic.fileutil import file_lines
from lockss.pybasic.nodeutil import NodeSet, get_node_spec_adapter
from pydantic import ValidationError
import yaml

from . import config, crawler, md, poller, rs, __copyright__, __license__, __version__
from ._core import LockssClient


#
# TYPE PLACEHOLDERS
#

_OpArgs = TypeVar('_OpArgs')


_OpResult = TypeVar('_OpResult')


_ResultKey = TypeVar('_ResultKey')


_ResultValue = TypeVar('_ResultValue')


#
# TYPE ALIASES
#

_YamlT: TypeAlias = Any


SwaggerModel: TypeAlias = Union[
    config.ApiStatus,
    crawler.ApiStatus,
    md.ApiStatus,
    poller.ApiStatus,
    rs.ApiStatus,
]


SwaggerModelT: TypeAlias = type[SwaggerModel]


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
        # REPOSITORY
        namespace: Optional[str] = None
        # Matrix-oriented output
        glyphs: Optional[bool] = None

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

    def get_checksum_algorithms(self) -> None:
        self._generic_node_matrix_action(LockssClient.get_supported_checksum_algorithms,
                                         _CHECKSUM_ALGORITHM_COLUMNS)

    def get_namespaces(self) -> None:
        self._generic_node_matrix_action(LockssClient.get_namespaces,
                                         _NAMESPACE_COLUMNS)

    def get_repository_service_status(self, **kwargs) -> None:
        self._generic_node_table_action(LockssClient.get_repository_service_status,
                                        _columns(rs.ApiStatus),
                                        needs_auth=False)

    #
    # CONFIGURATION
    #

    def get_configuration_service_status(self, **kwargs) -> None:
        self._generic_node_table_action(LockssClient.get_configuration_service_status,
                                        _columns(config.ApiStatus),
                                        needs_auth=False)

    #
    # POLLER
    #

    def get_poller_service_status(self, **kwargs) -> None:
        self._generic_node_table_action(LockssClient.get_poller_service_status,
                                        _columns(poller.ApiStatus),
                                        needs_auth=False)

    #
    # CRAWLER
    #

    def get_crawler_service_status(self, **kwargs) -> None:
        self._generic_node_table_action(LockssClient.get_crawler_service_status,
                                        _columns(crawler.ApiStatus),
                                        needs_auth=False)

    #
    # METADATA
    #

    def get_metadata_service_status(self, **kwargs) -> None:
        self._generic_node_table_action(LockssClient.get_metadata_service_status,
                                        _columns(md.ApiStatus),
                                        needs_auth=False)

    #
    # PROTECTED
    #

    def _generic_action(self,
                        operation: Callable[Concatenate[_OpArgs, dict[str, Any]], _OpResult],
                        args_and_kwargs: Sequence[tuple[_OpArgs, Optional[dict[str, Any]]]],
                        get_result: Optional[Callable[[_OpResult], _ResultValue]] = None,
                        get_label: Optional[Callable[[_OpArgs], str]] = None) \
            -> tuple[dict[_OpArgs, _ResultValue], Optional[dict[_OpArgs, Exception]]]:
        actual_get_result: Callable[[_OpResult], _ResultValue] = get_result or (lambda x: x)
        actual_get_label: Callable[[_OpArgs], str] = get_label or str
        results: dict[_OpArgs, _ResultValue] = {}
        errors: dict[_OpArgs, Exception] = {}
        with OperationTrail(jobs=(meta := self._ctx.meta)[JOBS],
                            total=(total_tasks := len(args_and_kwargs)),
                            progress_bar=True,
                            enabled=meta[PROGRESS]) as trail:
            def _one_task(arg_and_kwarg: tuple[_OpArgs, Optional[dict[str, Any]]]) -> None:
                arg: _OpArgs
                kwarg: Optional[dict[str, Any]]
                arg, kwarg = arg_and_kwarg
                label: str = actual_get_label(arg)
                try:
                    results[arg] = actual_get_result(operation(*arg, **(kwarg or {})))
                    trail.mark(True, label)
                except Exception as exc:
                    errors[arg] = exc
                    trail.mark(False, label)
            for _ in run_jobs(_one_task, args_and_kwargs):
                pass # I guess?
            trail.finish(trail.ok_count == total_tasks, f'{trail.ok_count}/{total_tasks} succeeded')
        return results, (errors or None)

    def _generic_node_action(self,
                             operation: Callable[Concatenate[tuple[LockssClient], dict[str, Any]], SwaggerModel],
                             needs_auth = True,
                             **kwargs) \
            -> tuple[dict[tuple[LockssClient], SwaggerModel], Optional[dict[tuple[LockssClient], Exception]]]:
        self._initialize_clients()
        if needs_auth:
            self._initialize_auth()
        # Could be a return statement but need to satisfy the type checker
        results: dict[tuple[LockssClient], SwaggerModel]
        errors: Optional[dict[tuple[LockssClient], Exception]]
        results, errors = self._generic_action(operation,
                                               [(arg, kwargs) for arg in [(client,) for client in self._clients]],
                                               get_label=lambda t: f'{t[0].get_id()}')
        return results, errors

    def _generic_node_matrix_action(self,
                                    operation: Callable[Concatenate[tuple[LockssClient], dict[str, Any]], SwaggerModel],
                                    result_columns: Sequence[ColumnSpec],
                                    **kwargs) -> None:
        results, errors = self._generic_node_action(operation, **kwargs)
        self._generic_matrix_output(results,
                                    errors,
                                    [(client,) for client in self._clients],
                                    [ColumnSpec(client.get_id(), client.get_id()) for client in self._clients],
                                    result_columns)

    def _generic_node_table_action(self,
                                   operation: Callable[Concatenate[tuple[LockssClient], dict[str, Any]], SwaggerModel],
                                   obj_columns: Sequence[ColumnSpec],
                                   needs_auth = True,
                                   **kwargs) -> None:
        results, errors = self._generic_node_action(operation,
                                                    needs_auth=needs_auth,
                                                    **kwargs)
        self._generic_table_output(results, errors, [(client,) for client in self._clients], (_NODE_COLUMN,), obj_columns)

    def _generic_matrix_output(self,
                               results: dict[_OpArgs, _ResultValue],
                               errors: Optional[dict[_OpArgs, Exception]],
                               args: Sequence[_OpArgs],
                               arg_columns: Sequence[ColumnSpec],
                               obj_columns: Sequence[ColumnSpec]) -> None:
        if errors: ### FIXME
            for k, v in errors.items(): print(repr(k), repr(v))
        table: list[Sequence[Optional[str]]] = []
        yes: str = OK_GLYPH if (glyphs := (opts := self._opts).glyphs) else str(True)
        no: str = KO_GLYPH if glyphs else str(False)
        row_values: set = set()
        for potential_row_value in results.values(): # Assumes potential_row_value is a sequence
            row_values.update(potential_row_value)
        for row_value in row_values:
            table.append([*[r if isinstance(r := row_value, Sequence) else [r]], *(yes if r in results[arg] else no for arg in args)])
        print_table(table,
                    headers=(*obj_columns, *arg_columns),
                    table_format=(meta := self._ctx.meta)[TABLE_FORMAT])

    def _generic_table_output(self,
                              results: dict[_OpArgs, _ResultValue],
                              errors: Optional[dict[_OpArgs, Exception]],
                              args: Sequence[_OpArgs],
                              arg_columns: Sequence[ColumnSpec],
                              result_columns: Sequence[ColumnSpec]) -> None:
        table: list[Sequence[Optional[str]]] = []
        selected_column_ids: Sequence[str] = (meta := self._ctx.meta)[COLUMNS] or ()
        obj_column_ids: Sequence[str] = tuple(obj_column.id for obj_column in result_columns)
        for arg in args:
            if arg in results:
                obj: _ResultValue = results[arg]
                d: dict = obj.to_dict() # FIXME only works if obj is SwaggerModel
                table.append([*map(str, [*arg, *select_row(d, selected_column_ids, obj_column_ids), ''])])
            elif errors and arg in errors:
                err: Exception = errors[arg]
                table.append([*map(str, [*arg, *[None for _ in result_columns], str(err)])])
            else:
                raise InternalError from KeyError(arg)
        print_table(table,
                    headers=(*arg_columns, *select_columns(result_columns, selected_column_ids or obj_column_ids), _ERROR_COLUMN),
                    table_format=(meta := self._ctx.meta)[TABLE_FORMAT])

    def _initialize_auth(self) -> None:
        u = opts.username if (opts := self._opts).username else prompt('UI username')
        p, opts.password = opts.password if opts.password else prompt('UI password', hide_input=True), None
        for client in self._clients:
            client.authenticate(u, p)

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
                    node_set_yaml: _YamlT = yaml.safe_load(node_set_input)
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
# COLUMN DESCRIPTORS
#

_AUID_COLUMN_ID: str = 'auid'


_AUID_COLUMN_DESCRIPTION: str = 'AUID'


_AUID_COLUMN: ColumnSpec = ColumnSpec(_AUID_COLUMN_ID, _AUID_COLUMN_DESCRIPTION)


_CHECKSUM_ALGORITHM_COLUMN_ID: str = 'checksum_algorithm'


_CHECKSUM_ALGORITHM_COLUMN_DESCRIPTION: str = 'Checksum Algorithm'


_CHECKSUM_ALGORITHM_COLUMN: ColumnSpec = ColumnSpec(_CHECKSUM_ALGORITHM_COLUMN_ID, _CHECKSUM_ALGORITHM_COLUMN_DESCRIPTION)


_ERROR_COLUMN_ID: str = 'error'


_ERROR_COLUMN_DESCRIPTION: str = 'Error'


_ERROR_COLUMN: ColumnSpec = ColumnSpec(_ERROR_COLUMN_ID, _ERROR_COLUMN_DESCRIPTION)


_NAMESPACE_COLUMN_ID: str = 'namespace'


_NAMESPACE_COLUMN_DESCRIPTION: str = 'Namespace'


_NAMESPACE_COLUMN: ColumnSpec = ColumnSpec(_NAMESPACE_COLUMN_ID, _NAMESPACE_COLUMN_DESCRIPTION)


_NODE_COLUMN_ID: str = 'node'


_NODE_COLUMN_DESCRIPTION: str = 'Node'


_NODE_COLUMN: ColumnSpec = ColumnSpec(_NODE_COLUMN_ID, _NODE_COLUMN_DESCRIPTION)


#
# COLUMN GROUPS
#


_AUID_COLUMNS: Sequence[ColumnSpec] = (_AUID_COLUMN,)


_CHECKSUM_ALGORITHM_COLUMNS: Sequence[ColumnSpec] = (_CHECKSUM_ALGORITHM_COLUMN,)


_NAMESPACE_AUID_COLUMNS: Sequence[ColumnSpec] = (_NAMESPACE_COLUMN, _AUID_COLUMN)


_NAMESPACE_COLUMNS: Sequence[ColumnSpec] = (_NAMESPACE_COLUMN,)


_NODE_COLUMNS: Sequence[ColumnSpec] = (_NODE_COLUMN,)


_NODE_AUID_COLUMNS: Sequence[ColumnSpec] = (_NODE_COLUMN, _AUID_COLUMN)


#
# OPTIONS
#

#: The use glyphs option: --use-glyphs
_glyphs_option = option('--glyphs/--no-glyphs', is_flag=True, show_default=True, help=f'Whether to use {OK_GLYPH}/{KO_GLYPH} glyphs instead of True/False')


#: The namespace option: --namespace, -n
_namespace_option = option('--namespace', '-n', metavar='NMSP', help='Set the artifact namespace to NMSP.')


#: The progress option: --progress / --no-progress
_progress_option = decorator_factory(dec=option, cls=ProgressOption)


#: The table format option: --table-format, -T
_table_format_option = table_format_option('--table-format', '-T')


#
# OPTION GROUPS
#

@cache
def _columns(swagger_model_type: SwaggerModelT) -> Sequence[ColumnSpec]:
    return tuple(ColumnSpec(obj_attr, ' '.join(word.capitalize() for word in obj_attr.split('_'))) for obj_attr in swagger_model_type.attribute_map)


def _matrix_output_option_group(result_columns: Sequence[ColumnSpec],
                                sort_default: Optional[Sequence[ColumnSpec]] = None):
    if sort_default:
        raise NotImplementedError
    return option_group(
        'Matrix output options',
        *((sort_by_option(columns=result_columns),) if len(result_columns) > 1 else ()),
        _table_format_option,
        _glyphs_option,
    )


def _table_output_option_group(key_columns: Sequence[ColumnSpec],
                               swagger_model_type: SwaggerModelT):
    result_columns: Sequence[ColumnSpec] = _columns(swagger_model_type)
    return option_group(
        'Table output options',
        columns_option(columns=result_columns),
        sort_by_option(columns=(*key_columns, *result_columns, _ERROR_COLUMN)),
        _table_format_option,
    )


#: The node option group: --node-set, -s; --node-spec; --node-specs; --username, -U; --password, -P
_node_option_group = option_group(
    'Node options',
    option('--node-set', '-s', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the nodes from the node set in FILE to the list of nodes to process.'),
    option('--node-spec', '--node', metavar='NODE', multiple=True, help='Add the compact node specification NODE to the list of nodes to process.'),
    option('--node-specs', '--nodes', metavar='FILE', type=click_path('ferz'), multiple=True, help='Add the compact node specifications in FILE to the list of nodes to process.'),
    option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the UI username to USER.'),
    option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the UI password to PASS.'),
)


#: The job option group: --jobs
_job_option_group = option_group(
    'Job options',
    jobs_option,
)


#: The display option group: --accessible; --color; --no-color; --progress/--no-progress
_display_option_group = option_group(
    'Display options',
    accessible_option,
    color_option,
    no_color_option,
    _progress_option,
)


#: The debug option group: --show-params, --time/--no-time
_debug_option_group = option_group(
    'Debug options',
    show_params_option,
    timer_option
)


def _generic_matrix_options(result_columns: Sequence[ColumnSpec],
                            additional_option_groups: Optional[Sequence] = None):
    return compose_decorators(
        _node_option_group,
        *(additional_option_groups if additional_option_groups else ()),
        _matrix_output_option_group(result_columns),
        _job_option_group,
        _display_option_group,
        _debug_option_group,
        pass_context
    )

def _generic_table_options(key_columns: Sequence[ColumnSpec],
                           swagger_model_type: Optional[SwaggerModelT] = None):
    return compose_decorators(
        _node_option_group if _NODE_COLUMN in key_columns else None,
        _table_output_option_group(key_columns, swagger_model_type) if swagger_model_type else None,
        _job_option_group,
        _display_option_group,
        _debug_option_group,
        pass_context
    )


#
# CLICK INFRASTRUCTURE
#

@group(params=None)
@tree_option
@pass_context
def locksscli(ctx: Context, **kwargs):
    pass


#: The composite top-level command decorator
_top_level_command = compose_decorators(_debug_option_group, pass_context)


@locksscli.command(help='Show the copyright and exit.')
@_top_level_command
def copyright(ctx: Context, **kwargs) -> None:
    echo(__copyright__)


@locksscli.command(help='Show the software license and exit.')
@_top_level_command
def license(ctx: Context, **kwargs) -> None:
    echo(__license__)


@locksscli.command(help='Show the version number and exit.')
@_top_level_command
def version(ctx: Context, **kwargs) -> None:
    echo(__version__)


#
# REPOSITORY
#

_REPOSITORY_COMMANDS = Section('Repository Service commands')


@locksscli.command(aliases=['ga'], section=_REPOSITORY_COMMANDS, help='Get AUIDs.')
@_generic_matrix_options(_NAMESPACE_AUID_COLUMNS, additional_option_groups=(option_group('Namespace options', _namespace_option),))
def get_auids(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_auids()


@locksscli.command(aliases=['gn'], section=_REPOSITORY_COMMANDS, help='Get namespaces.')
@_generic_matrix_options(_NAMESPACE_COLUMNS)
def get_namespaces(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_namespaces()


@locksscli.command(aliases=['grss'], section=_REPOSITORY_COMMANDS, help='Get the status of the LOCKSS Repository Service.')
@_generic_table_options(_NODE_COLUMNS, rs.ApiStatus)
def get_repository_service_status(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_repository_service_status()


@locksscli.command(aliases=['gsca'], section=_REPOSITORY_COMMANDS, help='Get supported checksum algorithms.')
@_generic_matrix_options(_CHECKSUM_ALGORITHM_COLUMNS)
def get_supported_checksum_algorithms(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_checksum_algorithms()


#
# CONFIGURATION
#

_CONFIGURATION_COMMANDS = Section('Configuration Service commands')


@locksscli.command(aliases=['gcss'], section=_CONFIGURATION_COMMANDS, help='Get the status of the LOCKSS Configuration Service.')
@_generic_table_options(_NODE_COLUMNS, config.ApiStatus)
def get_configuration_service_status(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_configuration_service_status()


#
# POLLER
#

_POLLER_COMMANDS = Section('Poller Service commands')


@locksscli.command(aliases=['gpss'], section=_POLLER_COMMANDS, help='Get the status of the LOCKSS Poller Service.')
@_generic_table_options(_NODE_COLUMNS, poller.ApiStatus)
def get_poller_service_status(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_poller_service_status()


#
# CRAWLER
#

_CRAWLER_COMMANDS = Section('Crawler Service commands')


@locksscli.command(aliases=['gwss'], section=_CRAWLER_COMMANDS, help='Get the status of the LOCKSS Crawler Service.')
@_generic_table_options(_NODE_COLUMNS, crawler.ApiStatus)
def get_crawler_service_status(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_crawler_service_status()


#
# METADATA
#

_METADATA_COMMANDS = Section('Metadata Service commands')


@locksscli.command(aliases=['gmss'], section=_METADATA_COMMANDS, help='Get the status of the LOCKSS Metadata Service.')
@_generic_table_options(_NODE_COLUMNS, md.ApiStatus)
def get_metadata_service_status(ctx: Context, **kwargs) -> None:
    _LockssCli(ctx, **kwargs).get_metadata_service_status()


def main() -> None:
    """Entry point for the locksscli command line tool."""
    locksscli()
