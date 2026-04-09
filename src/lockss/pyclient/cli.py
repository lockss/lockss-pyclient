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

from dataclasses import dataclass, field
from functools import partial
from importlib.metadata import entry_points
from inspect import ismethod

from click_extra import Choice, ExtraContext, Section, color_option, echo, group, option, option_group, pass_context, pass_obj, prompt, show_params_option
from click_plugins import with_plugins
from lockss.pybasic.cliutil import UInt16, click_path, compose_decorators, make_extra_context_settings
from lockss.pybasic.errorutil import InternalError

from lockss.pyclient.crawler import CrawlerStatus

from . import *
from . import __copyright__, __license__, __version__
from . import config, crawler, md, poller, rs
from .output import _FormatOpts, SwaggerObject, display, display_basic, make_output_option_group


@dataclass(kw_only=True)
class _Opts(_FormatOpts):
    # Node
    host: Optional[str] = None
    configuration_port: Optional[int] = None
    crawler_port: Optional[int] = None
    metadata_port: Optional[int] = None
    poller_port: Optional[int] = None
    repository_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = field(default=None, repr=False)
    # crawler, md, poller
    job_id: Optional[str] = None
    # config
    auid: Optional[str] = None
    section_name: Optional[str] = None
    user_account: Optional[str] = None
    url: Optional[str] = None
    if_match: Optional[str] = None
    if_modified_since: Optional[str] = None
    if_none_match: Optional[str] = None
    if_unmodified_since: Optional[str] = None
    # crawler
    crawler_id: Optional[str] = None
    media_type: Optional[str] = None
    # md
    doi: Optional[str] = None
    openurl_param: Optional[tuple[str, ...]] = None
    # poller
    poll_key: Optional[str] = None
    peer_id: Optional[str] = None
    repair_type: Optional[str] = None
    tally_type: Optional[str] = None
    voter_urls_type: Optional[str] = None
    # repo
    committed: Optional[bool] = None
    namespace: Optional[str] = None
    uuid: Optional[str] = None


    def get_repair_type(self) -> str:
        match val := self.repair_type:
            case poller.RepairTypeEnum.ACTIVE | poller.RepairTypeEnum.COMPLETED | poller.RepairTypeEnum.PENDING:
                return val
            case _:
                raise InternalError from ValueError(val)

    def get_tally_type(self) -> str:
        match val := self.tally_type:
            case poller.TallyTypeEnum.AGREE | poller.TallyTypeEnum.DISAGREE | poller.TallyTypeEnum.ERROR | poller.TallyTypeEnum.NOQUORUM | poller.TallyTypeEnum.TOOCLOSE:
                return val
            case _:
                raise InternalError from ValueError(val)

    def get_voter_urls_type(self) -> str:
        match val := self.voter_urls_type:
            case poller.VoterUrlsEnum.AGREED | poller.VoterUrlsEnum.DISAGREED | poller.VoterUrlsEnum.POLLERONLY | poller.VoterUrlsEnum.VOTERONLY:
                return val
            case _:
                raise InternalError from ValueError(val)


class _LockssApiCli(object):

    def __init__(self, ctx: ExtraContext):
        super().__init__()
        self._ctx: ExtraContext = ctx
        self._opts: Optional[_Opts] = None
        self._node: Optional[Node] = None
        self._auid: Optional[str] = None

    def config_aus_agreements(self) -> None:
        display_basic(self._opts, config_get_au_agreements(self._node, self._auid))

    def config_aus_configuration_get(self) -> None:
        display(self._opts, config_get_au_config(self._node, self._auid).au_config) # Note the .au_config

    def config_aus_configuration_get_all(self) -> None:
        display(self._opts, config_get_au_configs(self._node))

    def config_aus_no_au_peer_set(self) -> None:
        display(self._opts, config_get_no_au_peer_set(self._node, self._auid))

    def config_aus_state(self) -> None:
        display(self._opts, config_get_au_state(self._node, self._auid))

    def config_aus_status(self) -> None:
        display(self._opts, config_get_au_status(self._node, self._auid))

    def config_aus_suspect_urls(self) -> None:
        display(self._opts, config_get_au_suspect_url_versions(self._node).suspect_versions) # of type list[config.SuspectUrlVersion]

    def config_last_update_time(self) -> None:
        echo(config_last_update_time(self._node))

    def config_loaded_urls(self) -> None:
        for loaded_url in config_get_loaded_urls(self._node):
            echo(loaded_url)

    def config_platform(self) -> None:
        display(self._opts, config_get_platform_config(self._node))

    def config_section_get(self) -> None:
        mp: MultipartParser = config_get_section(self._node,
                                                 url=(opts := self._opts).url,
                                                 if_match=opts.if_match,
                                                 if_modified_since=opts.if_modified_since,
                                                 if_none_match=opts.if_none_match,
                                                 if_unmodified_since=opts.if_unmodified_since)
        for part in mp.parts(): # FIXME
            echo(f'NAME: {part.name}')
            echo(f'HEADERS:\n{part.headers}')
            echo(f'VALUE:\n{part.value}')

    def config_status(self) -> None:
        display(self._opts, config_get_status(self._node))

    def config_url(self) -> None:
        mp: MultipartParser = config_get_url(self._node,
                                             url=(opts := self._opts).url,
                                             if_match=opts.if_match,
                                             if_modified_since=opts.if_modified_since,
                                             if_none_match=opts.if_none_match,
                                             if_unmodified_since=opts.if_unmodified_since)
        for part in mp.parts(): # FIXME
            echo(f'NAME: {part.name}')
            echo(f'HEADERS:\n{part.headers}')
            echo(f'VALUE:\n{part.value}')

    def config_users_get(self) -> None:
        echo(config_get_user_account(self._node, self._opts.user_account))

    def config_users_usernames(self) -> None:
        for username in sorted(config_get_usernames(self._node)):
            echo(username)

    def crawler_crawlers_config(self) -> None:
        display(self._opts, crawler_get_crawler_config(self._node, self._opts.crawler_id))

    def crawler_crawlers_status(self) -> None:
        crawler_map: dict[str, CrawlerStatus] = crawler_get_crawler_statuses(self._node).crawler_map
        display_basic(self._opts, {k: v.to_dict() for k, v in crawler_map.items()})

    def crawler_crawls_get(self) -> None:
        display(self._opts, crawler_get_crawl(self._node, self._opts.job_id))

    def crawler_crawls_get_all(self) -> None:
        display(self._opts, crawler_get_crawls(self._node))

    def crawler_crawls_urls_errors(self) -> None:
        display(self._opts, crawler_get_crawl_errors(self._node, self._opts.job_id))

    def crawler_crawls_urls_excluded(self) -> None:
        display(self._opts, crawler_get_crawl_excluded(self._node, self._opts.job_id))

    def crawler_crawls_urls_fetched(self) -> None:
        display(self._opts, crawler_get_crawl_fetched(self._node, self._opts.job_id))

    def crawler_crawls_urls_media_types_get(self) -> None:
        display(self._opts, crawler_get_crawl_by_media_type(self._node, (opts := self._opts).job_id, opts.media_type))

    def crawler_crawls_urls_not_modified(self) -> None:
        display(self._opts, crawler_get_crawl_not_modified(self._node, self._opts.job_id))

    def crawler_crawls_urls_parsed(self) -> None:
        display(self._opts, crawler_get_crawl_parsed(self._node, self._opts.job_id))

    def crawler_crawls_urls_pending(self) -> None:
        display(self._opts, crawler_get_crawl_pending(self._node, self._opts.job_id))

    def crawler_jobs_get(self) -> None:
        display(self._opts, crawler_get_job(self._node, self._opts.job_id))

    def crawler_jobs_get_all(self) -> None:
        display(self._opts, crawler_get_jobs(self._node))

    def crawler_status(self) -> None:
        display(self._opts, crawler_get_status(self._node))

    def dispatch(self, method: Callable[[], None], **cli_kwargs):
        if not ismethod(method):
            raise InternalError() from ValueError(method)
        self._opts = _Opts(**cli_kwargs)
        self._initialize_node(method)
        method()

    def initialize_opts(self, opts: _Opts) -> None:
        self._opts = opts
        # self._repo is operation-dependent
        self._auid = opts.auid

    def md_get(self) -> None:
        display(self._opts, md_get_metadata(self._node, self._auid))

    def md_jobs_get(self) -> None:
        display(self._opts, md_get_job(self._node, self._opts.job_id))

    def md_jobs_get_all(self) -> None:
        display(self._opts, md_get_jobs(self._node))

    def md_query_doi(self) -> None:
        display(self._opts, md_doi_query(self._node, self._opts.doi))

    def md_query_openurl(self) -> None:
        display(self._opts, md_openurl_query(self._node, list(self._opts.openurl_param)))

    def md_status(self) -> None:
        display(self._opts, md_get_status(self._node))

    def poller_jobs_get(self) -> None:
        display(self._opts, poller_get_poll_status(self._node, self._opts.job_id))

    def poller_polls_as_poller_get(self) -> None:
        display(self._opts, poller_get_poller_poll(self._node, self._opts.poll_key))

    def poller_polls_as_poller_get_all(self) -> None:
        display(self._opts, poller_get_poller_polls(self._node))

    def poller_polls_as_voter_get(self) -> None:
        display(self._opts, poller_get_voter_poll(self._node, self._opts.poll_key))

    def poller_polls_as_voter_get_all(self) -> None:
        display(self._opts, poller_get_voter_polls(self._node))

    def poller_polls_peer_data(self) -> None:
        for url in poller_get_peer_data(self._node, (opts := self._opts).poll_key, opts.peer_id, opts.get_voter_urls_type()):
            echo(url)

    def poller_polls_repairs(self) -> None:
        display(self._opts, poller_get_repair_data(self._node, (opts := self._opts).poll_key, opts.get_repair_type()))

    def poller_polls_tallies(self) -> None:
        for url in poller_get_tally_urls(self._node, (opts := self._opts).poll_key, opts.get_tally_type()):
            echo(url)

    def poller_status(self) -> None:
        display(self._opts, poller_get_status(self._node))

    def repo_artifacts_delete(self) -> None:
        kwargs = {}
        if ns := (opts := self._opts).namespace:
            kwargs['namespace'] = ns
        repo_delete_artifact(self._node, opts.uuid, **kwargs)

    def repo_artifacts_update(self) -> None:
        kwargs = {}
        if ns := (opts := self._opts).namespace:
            kwargs['namespace'] = ns
        display(self._opts, repo_update_artifact(self._node, opts.uuid, opts.committed, **kwargs))

    def repo_aus_auids(self) -> None:
        kwargs = {}
        if ns := self._opts.namespace:
            kwargs['namespace'] = ns
        for auid in sorted(repo_get_auids(self._node, **kwargs)):
            echo(auid)

    def repo_aus_size(self) -> None:
        kwargs = {}
        if ns := self._opts.namespace:
            kwargs['namespace'] = ns
        display(self._opts, repo_get_au_size(self._node, self._auid, **kwargs))

    def repo_checksum_algorithms(self) -> None:
        for checksum_algorithm in sorted(repo_get_checksum_algorithms(self._node), key=lambda x: x.lower()):
            echo(checksum_algorithm)

    def repo_info(self) -> None:
        display(self._opts, repo_get_info(self._node))

    def repo_namespaces(self) -> None:
        for namespace in sorted(repo_get_namespaces(self._node)):
            echo(namespace)

    def repo_status(self) -> None:
        display(self._opts, repo_get_status(self._node))

    def repo_storage_info(self) -> None:
        display(self._opts, repo_get_storage_info(self._node))

    def _initialize_node(self, method: Callable[[], None]):
        prefix, underscore, suffix = method.__name__.partition('_')
        kwargs = {}
        opts = self._opts
        kw_prefix, opt_prefix = prefix, prefix
        match prefix:
            case 'config':
                opt_prefix = 'configuration'
            case 'crawler' | 'poller':
                pass
            case 'md':
                opt_prefix = 'metadata'
            case 'repo':
                kw_prefix, opt_prefix = 'rs', 'repository'
            case _:
                self._ctx.fail(f'Internal error: method name is not recognized')
        kwargs[f'{kw_prefix}_port'] = getattr(opts, f'{opt_prefix}_port')
        if suffix != 'status': # All five 'status' operations are passwordless
            if opts.username is None:
                opts.username = prompt('API username')
            if opts.password is None:
                opts.password = prompt('API password', hide_input=True)
        self._node = Node(opts.host, username=opts.username, password=opts.password, **kwargs)


#
# Options
#


def _make_port_option(long: str,
                      short: str,
                      default: int,
                      service: str):
    return option(f'--{long}-port', f'-{short}', metavar='PORT', type=UInt16, default=default, help=f'Set the {service} Service API port to PORT')


_auid_option = option('--auid', '-a', metavar='VALUE', required=True, help='Set the AUID to process to VALUE.')


_config_port_option = _make_port_option('configuration', 'C', CONFIG_DEFAULT_PORT, 'Configuration')


_crawler_port_option = _make_port_option('crawler', 'W', CRAWLER_DEFAULT_PORT, 'Crawler')


_headers_option = option('--headers/--no-headers', is_flag=True, default=True, help='Set whether to include HTTP headers in multipart output.')


_host_option = option('--host', '-h', metavar='HOST', required=True, help='Set the host of the node to be processed to HOST.')


_if_match_option = option('--if-match', metavar='VALUE', help='Set the If-Match HTTP header to VALUE.')


_if_modified_since_option = option('--if-modified-since', metavar='VALUE', help='Set the If-Modified-Since HTTP header to VALUE.')


_if_none_match_option = option('--if-none-match', metavar='VALUE', help='Set the If-None-Match HTTP header to VALUE.')


_if_unmodified_since_option = option('--if-unmodified-since', metavar='VALUE', help='Set the If-Unmodified-Since HTTP header to VALUE.')


_md_port_option = _make_port_option('metadata', 'M', MD_DEFAULT_PORT, 'Metadata')


_namespace_option = option('--namespace', '-n', metavar='NAMESPACE', help='Set the namespace to NAMESPACE.')


_output_file_option = option('--output-file', '-o', metavar='FILE', type=click_path('fwz'), show_default='console output', help='Output the multipart body to the file FILE.')


_password_option = option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the API password to PASS.')


_peer_id_option = option('--peer-id', '-p', metavar='PEER', required=True, help='Set the peer ID to PEER.')


_poller_port_option = _make_port_option('poller', 'L', POLLER_DEFAULT_PORT, 'Poller')


_repo_port_option = _make_port_option('repository', 'R', RS_DEFAULT_PORT, 'Repository')


_url_option = option('--url', '-u', metavar='VALUE', help='Set the URL to VALUE.')


_uuid_option = option('--uuid', '-w', metavar='VALUE', required=True, help='Set the UUID to VALUE.')


_username_option = option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the API username to USER.')


_voter_url_type_option = option('--voter-url-type', type=Choice(((vue := poller.VoterUrlsEnum).AGREED, vue.DISAGREED, vue.POLLERONLY, vue.VOTERONLY)), required=True, help='Set the voter URL type to the given type.')


#
# Option groups
#

def _make_node_option_group(port_option):
    return option_group('Node options', _host_option, _username_option, _password_option, port_option)


_artifact_namespace_uuid_option_group = option_group('Artifact options', _namespace_option, _uuid_option)


_auid_option_group = option_group('AUID options', _auid_option)


_commit_option_group = option_group('Commit options', option('--committed/--not-committed', is_flag=True, required=True, help="Set the artifact's committed flag to the given state."))


_config_node_option_group = _make_node_option_group(_config_port_option)


_crawler_option_group = option_group('Crawler options', option('--crawler-id', '-c', metavar='IDENT', required=True, help='Set the crawler identifier to IDENT.'))


_crawler_node_option_group = _make_node_option_group(_crawler_port_option)


_doi_option_group = option_group('DOI options', option('--doi', '-d', metavar='VALUE', required=True, help='Set the DOI to VALUE.'))


_job_option_group = option_group('Job options', option('--job-id', '-i', metavar='JOBID', required=True, help='Set the job ID to JOBID'))


_md_node_option_group = _make_node_option_group(_md_port_option)


_media_type_option_group = option_group('Media type options', option('--media-type', '-m', metavar='TYPE', required=True, help='Set the media type to TYPE.'))


_multipart_output_options = option_group('Multipart output options', _headers_option, _output_file_option)


_namespace_option_group = option_group('Namespace options', _namespace_option)


_openurl_option_group = option_group('OpenURL options', option('--openurl-param', '-p', metavar='VALUE', required=True, multiple=True, help='Add VALUE to the list of OpenURL parameters.'))


_peer_data_option_group = option_group('Peer data options', _peer_id_option, _voter_url_type_option)


_poll_key_option_group = option_group('Poll key options', option('--poll-key', '-k', metavar='KEY', required=True, help='Set the poll key to KEY.'))


_poller_node_option_group = _make_node_option_group(_poller_port_option)


_repair_type_option_group = option_group('Repair type options', option('--repair-type', type=Choice(((rte := poller.RepairTypeEnum).ACTIVE, rte.COMPLETED, rte.PENDING)), required=True, help='Set the repair type to the given type.'))


_repo_node_option_group = _make_node_option_group(_repo_port_option)


_section_option_group = option_group('Section options', option('--section-name', '-s', metavar='NAME', required=True, help='Set the section name to NAME.'))


_tally_type_option_group = option_group('Tally type options', option('--tally-type', type=Choice(((tt := poller.TallyTypeEnum).AGREE, tt.DISAGREE, tt.ERROR, tt.NOQUORUM, tt.TOOCLOSE)), required=True, help='Set the repair type to the given type.'))


_url_option_group = option_group('URL options', _url_option)


_url_match_option_group = option_group('URL match options', _if_match_option, _if_modified_since_option, _if_none_match_option, _if_unmodified_since_option)


_user_account_option_group = option_group('User account options', option('--user-account', '-u', metavar='NAME', required=True, help='Set the user account name to NAME.'))


#
# Command decorators
#

def _make_command(node_option_group: Callable,
                  parent: Callable,
                  name: str,
                  help: str,
                  *inputs,
                  output_cls: Optional[type[SwaggerObject]] = None,
                  output_dec: Optional[Callable] = None):
    output_tuple: Optional[tuple[Callable]] = None
    if output_cls:
        output_tuple = (make_output_option_group(output_cls),)
    elif output_dec:
        output_tuple = (output_dec,)
    return compose_decorators(parent.command(name, help=help), node_option_group, *inputs, *(output_tuple or ()), pass_obj)


_make_config_command = partial(_make_command, _config_node_option_group)


_make_crawler_command = partial(_make_command, _crawler_node_option_group)


_make_md_command = partial(_make_command, _md_node_option_group)


_make_poller_command = partial(_make_command, _poller_node_option_group)


_make_repo_command = partial(_make_command, _repo_node_option_group)


#
# Top-level
#

@with_plugins(entry_points(module='click_command_tree')) # adds a 'tree' command
@group('lockssapi', params=None, context_settings=make_extra_context_settings())
@color_option
@show_params_option
@pass_context
def _lockssapi(ctx: ExtraContext, **kwargs):
    ctx.obj = _LockssApiCli(ctx)


_SUBCOMMANDS = Section('Subcommands')


@_lockssapi.command('copyright', help='Show the copyright and exit.')
def _copyright() -> None:
    echo(__copyright__)


@_lockssapi.command('license', help='Show the software license and exit.')
def _license() -> None:
    echo(__license__)


# 'tree' command implied by click_command_tree plugin


@_lockssapi.command('version', help='Show the version number and exit.')
def _version() -> None:
    echo(__version__)


#
# config
#

@_lockssapi.group('config', section=_SUBCOMMANDS, help='Subcommand for Configuration Service operations.')
def _config():
    pass


_SUBCOMMANDS_CONFIG = Section('Subcommands')


@_make_config_command(_config, 'last-update-time', 'Get the timestamp when the configuration was last updated.')
def _config_last_update_time(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.config_last_update_time, **kwargs)


@_make_config_command(_config, 'loaded-urls', 'Get the URLs from which the configuration was loaded.')
def _config_loaded_urls(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.config_loaded_urls, **kwargs)


@_make_config_command(_config, 'platform', 'Get the platform configuration.', output_cls=config.PlatformConfigurationWsResult)
def _config_platform(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.config_platform, **kwargs)


@_make_config_command(_config, 'status', 'Get the status of the Configuration Service.', output_cls=config.ApiStatus)
def _config_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.config_status, **kwargs)


@_make_config_command(_config, 'url', 'Get the file for a configuration URL.', _url_option_group, _url_match_option_group, output_dec=_multipart_output_options)
def _config_url(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.config_url, **kwargs)


#
# config aus
#

@_config.group('aus', section=_SUBCOMMANDS_CONFIG, help='Subcommand for AU operations.')
def _config_aus():
    pass


_SUBCOMMANDS_CONFIG_AUS = Section('Subcommands')


@_make_config_command(_config_aus, 'agreements', 'Get the poll agreements of an AU.', _auid_option_group)
def _config_aus_agreements(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_agreements, **kwargs)


@_make_config_command(_config_aus, 'no-au-peer-set', 'Get the NoAuPeerSet object of an AU.', _auid_option_group, output_dec=make_output_option_group(config.DatedPeerIdSetImpl, basic_default=True))
def _config_aus_no_au_peer_set(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_no_au_peer_set, **kwargs)


@_make_config_command(_config_aus, 'state', 'Get the state of an AU.', _auid_option_group, output_cls=config.AuStateBean)
def _config_aus_state(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_state, **kwargs)


@_make_config_command(_config_aus, 'status', 'Get the status of an AU.', _auid_option_group, output_cls=config.AuStatus)
def _config_aus_status(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_status, **kwargs)


@_make_config_command(_config_aus, 'suspect-urls', 'Get the suspect URL versions of an AU.', _auid_option_group, output_cls=config.SuspectUrlVersion)
def _config_aus_suspect_urls(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_suspect_urls, **kwargs)


#
# config aus configuration
#

@_config_aus.group('configuration', section=_SUBCOMMANDS_CONFIG_AUS, help='Subcommand for AU configuration operations.')
def _config_aus_configuration():
    pass


@_make_config_command(_config_aus_configuration, 'get', 'Get the configuration of an AU.', _auid_option_group, output_dec=make_output_option_group(config.AuConfiguration, basic_default=True))
def _config_aus_configuration_get(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_configuration_get, **kwargs)


@_make_config_command(_config_aus_configuration, 'get-all', 'Get the configuration of an AU.', output_cls=config.AuConfiguration)
def _config_aus_configuration_get_all(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_aus_configuration_get_all, **kwargs)


#
# config section
#

@_config.group('section', section=_SUBCOMMANDS_CONFIG, help='Subcommand for section operations.')
def _config_section():
    pass


@_make_config_command(_config_section, 'get', 'Get the named configuration file.', _section_option_group, _url_match_option_group, output_dec=_multipart_output_options)
def _config_section_get(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_section_get, **kwargs)


#
# config users
#

@_config.group('users', section=_SUBCOMMANDS_CONFIG, help='Subcommand for user operations.')
def _config_users():
    pass


@_make_config_command(_config_users, 'get', 'Get user account details.', _user_account_option_group, output_cls=crawler.ApiStatus)
def _config_users_get(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_users_get, **kwargs)


@_make_config_command(_config_users, 'username', 'Get the usernames configured in the system.')
def _config_users_usernames(cli: _LockssApiCli, **kwargs):
    cli.dispatch(cli.config_users_usernames, **kwargs)


#
# crawler
#

@_lockssapi.group('crawler', section=_SUBCOMMANDS, help='Subcommand for Crawler Service operations.')
def _crawler():
    pass


@_make_crawler_command(_crawler, 'status', 'Get the status of the Crawler Service.', output_cls=crawler.ApiStatus)
def _crawler_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_status, **kwargs)


_SUBCOMMANDS_CRAWLER = Section('Subcommands')


#
# crawler crawlers
#

@_crawler.group('crawlers', section=_SUBCOMMANDS_CRAWLER, help='Subcommand for crawler information operations.')
def _crawler_crawlers():
    pass


@_make_crawler_command(_crawler_crawlers, 'config', 'Get the configuration information related to an installed crawler.', _crawler_option_group, output_cls=crawler.CrawlerConfig)
def _crawler_crawlers_config(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawlers_config, **kwargs)


@_make_crawler_command(_crawler_crawlers, 'status', 'Get the status of installed crawlers.')
def _crawler_crawlers_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawlers_status, **kwargs)


#
# crawler crawls
#

@_crawler.group('crawls', section=_SUBCOMMANDS_CRAWLER, help='Subcommand for crawl operations.')
def _crawler_crawls():
    pass


_SUBCOMMANDS_CRAWLER_CRAWLS = Section('Subcommands')


@_make_crawler_command(_crawler_crawls, 'get', 'Get the crawl status of a job.', _job_option_group, output_cls=crawler.CrawlStatus)
def _crawler_crawls_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_get, **kwargs)


@_make_crawler_command(_crawler_crawls, 'get-all', 'Get the list of crawls.', output_cls=crawler.CrawlStatus)
def _crawler_crawls_get_all(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_get_all, **kwargs)


#
# crawler crawls urls
#

@_crawler_crawls.group('urls', section=_SUBCOMMANDS_CRAWLER_CRAWLS, help='Subcommand for crawl operations.')
def _crawler_crawls_urls():
    pass


_SUBCOMMANDS_CRAWLER_CRAWLS_URLS = Section('Subcommands')


@_make_crawler_command(_crawler_crawls_urls, 'errors', 'Get the error URLs for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_errors(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_errors, **kwargs)


@_make_crawler_command(_crawler_crawls_urls, 'excluded', 'Get the excluded URLs for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_excluded(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_excluded, **kwargs)



@_make_crawler_command(_crawler_crawls_urls, 'fetched', 'Get the fetched URLs for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_fetched(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_fetched, **kwargs)


@_make_crawler_command(_crawler_crawls_urls, 'not-modified', 'Get the not modified URLs for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_not_modified(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_not_modified, **kwargs)


@_make_crawler_command(_crawler_crawls_urls, 'parsed', 'Get the parsed URLs for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_parsed(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_parsed, **kwargs)


@_make_crawler_command(_crawler_crawls_urls, 'pending', 'Get the pending URLs for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_pending(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_pending, **kwargs)


#
# crawler crawls urls media-types
#

@_crawler_crawls_urls.group('media-types', section=_SUBCOMMANDS_CRAWLER_CRAWLS_URLS, help='Subcommand for media type operations.')
def _crawler_crawls_urls_media_types():
    pass


@_make_crawler_command(_crawler_crawls_urls_media_types, 'get', 'Get the URLs of a given media type for a crawl.', _job_option_group, output_cls=crawler.UrlInfo)
def _crawler_crawls_urls_media_types_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_crawls_urls_media_types_get, **kwargs)


#
# crawler jobs
#

@_crawler.group('jobs', section=_SUBCOMMANDS_CRAWLER, help='Subcommand for crawler job operations.')
def _crawler_jobs():
    pass


@_make_crawler_command(_crawler_jobs, 'get', 'Get the status of a crawler job.', _job_option_group, output_cls=crawler.CrawlJob)
def _crawler_jobs_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_jobs_get, **kwargs)


@_make_crawler_command(_crawler_jobs, 'get-all', help='Get the status of all crawler jobs.', output_cls=crawler.CrawlJob)
def _crawler_jobs_get_all(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.crawler_jobs_get_all, **kwargs)


#
# md
#

@_lockssapi.group('md', section=_SUBCOMMANDS, help='Subcommand for Metadata Service operations.')
def _md():
    pass


_SUBCOMMANDS_MD = Section('Subcommands')


@_make_md_command(_md, 'get', 'Get the metadata stored for an AU.', output_cls=md.ItemMetadata)
def _md_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.md_get, **kwargs)


@_make_md_command(_md, 'status', 'Get the status of the Metadata Service.', output_cls=md.ApiStatus)
def _md_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.md_status, **kwargs)


#
# md jobs
#

@_md.group('jobs', section=_SUBCOMMANDS_MD, help='Subcommand for metadata job operations.')
def _md_jobs():
    pass


@_make_md_command(_md_jobs, 'get', 'Get queued job status.', _job_option_group, output_cls=md.Job)
def _md_jobs_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.md_jobs_get, **kwargs)


@_make_md_command(_md_jobs, 'get-all', 'Get the list of queued jobs.', output_cls=md.Job)
def _md_jobs_get_all(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.md_jobs_get_all, **kwargs)


#
# md query
#

@_md.group('query', section=_SUBCOMMANDS_MD, help='Subcommand for query operations.')
def _md_query():
    pass


@_make_md_command(_md_query, 'doi', 'Perform a DOI query.', _doi_option_group, output_cls=md.UrlInfo)
def _md_query_doi(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.md_query_doi, **kwargs)


@_make_md_command(_md_query, 'openurl', 'Perform an OpenURL query.', _openurl_option_group, output_cls=md.UrlInfo)
def _md_query_openurl(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.md_query_openurl, **kwargs)


#
# poller
#

@_lockssapi.group('poller', section=_SUBCOMMANDS, help='Subcommand for Poller Service operations.')
def _poller():
    pass


_SUBCOMMANDS_POLLER = Section('Subcommands')


@_make_poller_command(_poller, 'status', 'Get the status of the Poller Service.', output_cls=poller.ApiStatus)
def _poller_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_status, **kwargs)


#
# poller jobs
#

@_poller.group('jobs', section=_SUBCOMMANDS_POLLER, help='Subcommand for poller job operations.')
def _poller_jobs():
    pass


@_make_poller_command(_poller_jobs, 'get', 'Get the status of a poller job.', _job_option_group, output_cls=poller.PollerSummary)
def _poller_jobs_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_jobs_get, **kwargs)


#
# poller polls
#


@_poller.group('polls', section=_SUBCOMMANDS_POLLER, help='Subcommand for poll operations.')
def _poller_polls():
    pass


_SUBCOMMANDS_POLLER_POLLS = Section('Subcommands')


@_make_poller_command(_poller_polls, 'peer-data', 'Get peer data for a poll.', _poll_key_option_group, _peer_data_option_group, output_cls=poller.PeerData)
def _poller_polls_peer_data(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_peer_data, **kwargs)


@_make_poller_command(_poller_polls, 'repairs', 'Get the repairs for a poll.', _poll_key_option_group, _repair_type_option_group, output_cls=poller.RepairData)
def _poller_polls_repairs(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_repairs, **kwargs)


@_make_poller_command(_poller_polls, 'tallies', 'Get the tallies for a poll.', _poll_key_option_group, _tally_type_option_group, output_cls=poller.TallyData)
def _poller_polls_tallies(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_tallies, **kwargs)


#
# poller polls as-poller
#

@_poller_polls.group('as-poller', section=_SUBCOMMANDS_POLLER_POLLS, help='Subcommand for poller poll operations.')
def _poller_polls_as_poller():
    pass


@_make_poller_command(_poller_polls_as_poller, 'get', 'Get detailed information about a poll in which a node is the poller.', _poll_key_option_group, output_cls=poller.PollerDetail)
def _poller_polls_as_poller_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_as_poller_get, **kwargs)


@_make_poller_command(_poller_polls_as_poller, 'get-all', 'Get summary information about polls in which a node is the poller.', output_cls=poller.PollerSummary)
def _poller_polls_as_poller_get_all(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_as_poller_get_all, **kwargs)


#
# poller polls as-voter
#

@_poller_polls.group('as-voter', section=_SUBCOMMANDS_POLLER_POLLS, help='Subcommand for voter poll operations.')
def _poller_polls_as_voter():
    pass


@_make_poller_command(_poller_polls_as_voter, 'get', 'Get detailed information about a poll in which a node is a voter.', _poll_key_option_group, output_cls=poller.VoterDetail)
def _poller_polls_as_voter_get(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_as_voter_get, **kwargs)


@_make_poller_command(_poller_polls_as_voter, 'get-all', help='Get summary information about polls in which a node is a voter.', output_cls=poller.VoterSummary)
def _poller_polls_as_voter_get_all(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.poller_polls_as_voter_get_all, **kwargs)


#
# repo
#

@_lockssapi.group('repo', section=_SUBCOMMANDS, help='Subcommand for Repository Service operations.')
def _repo():
    pass


_SUBCOMMANDS_REPO = Section('Subcommands')


@_make_repo_command(_repo, 'checksum-algorithms', 'Get the supported checksum algorithms.')
def _repo_checksum_algorithms(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_checksum_algorithms, **kwargs)


@_make_repo_command(_repo, 'info', help='Get repository information.', output_dec=make_output_option_group(rs.RepositoryInfo, basic_default=True))
def _repo_info(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_info, **kwargs)


@_make_repo_command(_repo, 'namespaces', help='Get namespaces of the committed artifacts in the repository.')
def _repo_namespaces(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_namespaces, **kwargs)


@_make_repo_command(_repo, 'status', help='Get the status of the Repository Service.', output_cls=rs.ApiStatus)
def _repo_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_status, **kwargs)


@_make_repo_command(_repo, 'storage-info', help='Get repository storage information.', output_cls=rs.StorageInfo)
def _repo_storage_info(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_storage_info, **kwargs)


#
# repo artifacts
#

@_repo.group('artifacts', section=_SUBCOMMANDS_REPO, help='Subcommand for artifact operations.')
def _repo_artifacts():
    pass


_SUBCOMMANDS_REPO_ARTIFACTS = Section('Subcommands')


@_make_repo_command(_repo_artifacts, 'delete', 'Delete an artifact.', _artifact_namespace_uuid_option_group)
def _repo_artifacts_delete(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_artifacts_delete, **kwargs)


@_make_repo_command(_repo_artifacts, 'update', 'Update an artifact.', _artifact_namespace_uuid_option_group, _commit_option_group)
def _repo_artifacts_update(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_artifacts_update, **kwargs)


#
# repo artifacts get
#

@_repo_artifacts.group('get', section=_SUBCOMMANDS_REPO, help='Subcommand for artifact retrieval operations.')
def _repo_artifacts_get():
    pass


_SUBCOMMANDS_REPO_ARTIFACTS_GET = Section('Subcommands')


#
# FIXME
#

#
# repo aus
#

@_repo.group('aus', section=_SUBCOMMANDS_REPO, help='Subcommand for archival unit operations.')
def _repo_aus():
    pass


@_make_repo_command(_repo_aus, 'auids', 'Get archival unit IDs (AUIDs) in a namespace.', _namespace_option_group)
def _repo_aus_auids(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_aus_auids, **kwargs)


@_make_repo_command(_repo_aus, 'size', 'Get the size of artifacts in a namespace.', _namespace_option_group, _auid_option_group, output_cls=rs.AuSize)
def _repo_aus_size(cli: _LockssApiCli, **kwargs) -> None:
    cli.dispatch(cli.repo_aus_size, **kwargs)


def main() -> None:
    """
    Entry point for the lockssapi command line tool.
    """
    _lockssapi()


if __name__ == '__main__':
    main()
