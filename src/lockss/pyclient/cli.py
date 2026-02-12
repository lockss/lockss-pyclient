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

from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path
from typing import Literal
import sys

from click import Choice
from click_extra import ExtraContext, color_option, command, echo, group, option, option_group, pass_context, pass_obj, password_option, show_params_option
from lockss.pybasic.cliutil import NonNegativeInt, make_extra_context_settings

'''
from lockss.pybasic.cliutil import BaseCli, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, VERSION_DESCRIPTION
from lockss.pybasic.errorutil import InternalError
from pydantic.v1 import BaseModel as BaseModel1, Field as Field1, NonNegativeInt as NonNegativeInt1, root_validator as root_validator1

from .output import output_options
'''
from . import *
from . import __copyright__, __license__, __version__
from ._internal_common import _param_default, _RS
from . import config, crawler, md, poller, rs
from .output import _FormatOpts, display, make_output_option_group

'''
class NodeOptions(BaseModel1):
    host: str = Field1(aliases=["-H"], description="The IP address or FQDN of the LOCKSS node, optionally followed by a colon and port number")
    repo: NonNegativeInt1 = Field1(RS_DEFAULT_PORT, aliases=['--repository-port', '-R'], description='Repository Service port')
    config: NonNegativeInt1 = Field1(CONFIG_DEFAULT_PORT, aliases=['--configuration-port', '-C'], description='Configuration Service port')
    poller: NonNegativeInt1 = Field1(POLLER_DEFAULT_PORT, aliases=['--poller-port', '-L'], description='Poller Service port')
    crawler: NonNegativeInt1 = Field1(CRAWLER_DEFAULT_PORT, aliases=['--crawler-port', '-W'], description='Crawler Service port')
    md: NonNegativeInt1 = Field1(MD_DEFAULT_PORT, aliases=['--metadata-port', '-M'], description='Metadata Service port')

    def make_node(self, **kwargs) -> Node:
        return Node(self.host,
                    rs_port=self.repo,
                    config_port=self.config,
                    poller_port=self.poller,
                    crawler_port=self.crawler,
                    md_port=self.md,
                    **kwargs)


class AuthOptions(NodeOptions):
    username: str = Field1(aliases=["-U"], description="Username")
    password: Optional[str] = Field1(aliases=["-P"], description="Password")

    def make_node(self) -> Node:
        return super().make_node(username=self.username,
                                 password=self.password)


class NamespaceOptions(BaseModel1):
    namespace: Optional[str] = Field1(aliases=["-n"], description="Namespace")

    def get_namespace(self, default: str):
        return self.namespace if self.namespace else default


class AuidOptions(NamespaceOptions):
    auid: str = Field1(aliases=['-a'], description='Archival Unit identifier (AUID)')


class CrawlerIdOptions(BaseModel1):
    crawler_id: str = Field1(alias='crawler-id', aliases=['-c'], description='crawler identifier')


class DoiOptions(BaseModel1):
    doi: str = Field1(aliases=['-d'], description='DOI')


class IfMatchOptions(BaseModel1):
    if_match: Optional[str] = Field1(description='set the If-Match HTTP header to the given value')
    if_modified_since: Optional[str] = Field1(description='set the If-Modified-Since HTTP header to the given value')
    if_none_match: Optional[str] = Field1(description='set the If-None-Match HTTP header to the given value')
    if_unmodified_since: Optional[str] = Field1(description='set the If-Unmodified-Since HTTP header to the given value')


class JobOptions(BaseModel1):
    job: str = Field1(description='job identifier')


class OpenUrlOptions(BaseModel1):
    params: list[str] = Field1(aliases=['-p'], description='cumulative list of OpenURL parameters')


class OutputOptions(BaseModel1):
    output: Optional[Path] = Field1(aliases=['-o'], description='write output to the given file')


class PollKeyOptions(BaseModel1):
    poll_key: str = Field1(aliases=['-k'], description='poll key')


class PeerIdOptions(PollKeyOptions):
    peer_id: str = Field1(aliases=['-p'], description='peer identifier')
    agreed: bool = Field1(False, description='return the agreed peer URLs')
    disagreed: bool = Field1(False, description='return the disagreed peer URLs')
    poller_only: bool = Field1(False, description='return the poller-only peer URLs')
    voter_only: bool = Field1(False, description='return the voter-only peer URLs')

    @root_validator1
    def _validate_exactly_one(cls, values):
        attrs = ('agreed', 'disagreed', 'poller_only', 'voter_only')
        if len([attr for attr in attrs if values.get(attr)]) != 1:
            raise ValueError('Expected exactly one of {", ".join(f"--{hattr}" for hattr in [attr.replace("_", "-") for attr in attrs])}')
        return values

    def get_voter_urls_enum(self) -> poller.VoterUrlsEnum:
        if self.agreed: return poller.VoterUrlsEnum.AGREED
        elif self.disagreed: return poller.VoterUrlsEnum.DISAGREED
        elif self.poller_only: return poller.VoterUrlsEnum.POLLERONLY
        elif self.voter_only: return poller.VoterUrlsEnum.VOTERONLY
        else: raise InternalError from ValueError(self.json())

class RepairTypeOptions(BaseModel1):
    active: bool = Field1(False, description='return the active repairs')
    completed: bool = Field1(False, description='return the completed repairs')
    pending: bool = Field1(False, description='return the pending repairs')

    @root_validator1
    def _validate_exactly_one(cls, values):
        attrs = ('active', 'completed', 'pending')
        if len([attr for attr in attrs if values.get(attr)]) != 1:
            raise ValueError('Expected exactly one of {", ".join(f"--{hattr}" for hattr in [attr.replace("_", "-") for attr in attrs])}')
        return values

    def get_repair_type_enum(self) -> poller.RepairTypeEnum:
        if self.active: return poller.RepairTypeEnum.ACTIVE
        elif self.completed: return poller.RepairTypeEnum.COMPLETED
        elif self.pending: return poller.RepairTypeEnum.PENDING
        else: raise InternalError from ValueError(self.json())


class TallyTypeOptions(BaseModel1):
    agree: bool = Field1(False, description='return the tallies for URLs that agree')
    disagree: bool = Field1(False, description='return the tallies for URLs that disagree')
    error: bool = Field1(False, description='return the tallies for URLs that have errors')
    no_quorum: bool = Field1(False, description='return the tallies for URLs that have no quorum')
    too_close: bool = Field1(False, description='return the tallies for URLs that are too close')

    @root_validator1
    def _validate_exactly_one(cls, values):
        attrs = ('active', 'completed', 'pending')
        if len([attr for attr in attrs if values.get(attr)]) != 1:
            raise ValueError('Expected exactly one of {", ".join(f"--{hattr}" for hattr in [attr.replace("_", "-") for attr in attrs])}')
        return values

    def get_tally_type_enum(self) -> poller.TallyTypeEnum:
        if self.agree: return poller.TallyTypeEnum.AGREE
        elif self.disagree: return poller.TallyTypeEnum.DISAGREE
        elif self.error: return poller.TallyTypeEnum.ERROR
        elif self.no_quorum: return poller.TallyTypeEnum.NOQUORUM
        elif self.too_close: return poller.TallyTypeEnum.TOOCLOSE
        else: raise InternalError from ValueError(self.json())


class UrlOptions(BaseModel1):
    url: Optional[str] = Field1(aliases=['-u'], description='URL')


class UrlPrefixOptions(UrlOptions):
    url_prefix: Optional[str] = Field1(aliases=['-p'], description='URL prefix')

    @root_validator1
    def _validate_exactly_one(cls, values):
        attrs = ('url', 'url_prefix')
        if len([attr for attr in attrs if values.get(attr)]) != 1:
            raise ValueError('Expected exactly one of {", ".join(f"--{hattr}" for hattr in [attr.replace("_", "-") for attr in attrs])}')
        return values


class UuidOptions(NamespaceOptions):
    uuid: str = Field1(aliases=['-w'], description='artifact identifier')


class UncommittedOptions(BaseModel1):
    uncommitted: bool = Field1(False, description='include uncommitted artifacts in results')


class UserAccountOptions(BaseModel1):
    user_account: str = Field1(description='user account name')


class VersionsOptions(BaseModel1):
    all: bool = Field1(False, description='include all versions of artifacts in results')
    latest: bool = Field1(False, description='include only the latest version of artifacts in results')

    @root_validator1
    def _validate_at_most_one(cls, values):
        attrs = ('all', 'latest')
        if len([attr for attr in attrs if values.get(attr)]) > 1:
            raise ValueError('Expected at most one of {", ".join(f"--{hattr}" for hattr in [attr.replace("_", "-") for attr in attrs])}')
        return values

    def get_versions_enum(self, default: rs.VersionsEnum) -> rs.VersionsEnum:
        if self.all: return rs.VersionsEnum.ALL
        elif self.latest: return rs.VersionsEnum.LATEST
        else: return default


ArtifactOptions = output_options('ArtifactOptions', rs.Artifact, disambiguate=['auid', 'namespace'])


AuConfigurationOptions = output_options('AuConfigurationOptions', config.AuConfiguration)


CrawlJobOptions = output_options('CrawlJobOptions', crawler.CrawlJob)


CrawlStatusOptions = output_options('CrawlStatusOptions', crawler.CrawlStatus)


CrawlUrlInfoOptions = output_options('CrawlUrlInfoOptions', crawler.UrlInfo)


MdJobOptions = output_options('MdJobOptions', md.Job)


MdUrlInfoOptions = output_options('MdUrlInfoOptions', md.UrlInfo)


class LockssApi(BaseModel1):

    class Config(BaseModel1):

        class Aus(BaseModel1):

            class Agreements(AuidOptions, AuthOptions): pass

            class Configuration(BaseModel1):

                class Get(AuConfigurationOptions, AuidOptions, AuthOptions): pass

                class GetAll(AuConfigurationOptions, AuthOptions): pass

                get: Optional[Get] = Field1(description='Get the configuration of an AU')
                get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the configurations of all AUs')

            class NoAuPeerSet(output_options('DatedPeerIdSetImplOptions', config.DatedPeerIdSetImpl), AuidOptions, AuthOptions): pass

            class State(output_options('AuStateBeanOptions', config.AuStateBean, disambiguate=['auid']), AuidOptions, AuthOptions): pass

            class Status(output_options('AuStatusOptions', config.AuStatus), AuidOptions, AuthOptions): pass

            class SuspectUrls(output_options('SuspectUrlVersionOptions', config.SuspectUrlVersion), AuidOptions, AuthOptions): pass

            agreements: Optional[Agreements] = Field1(descriptions='Get the poll agreements of an AU')
            configuration: Optional[Configuration] = Field1(description='AU configuration operations')
            no_au_peer_set: Optional[NoAuPeerSet] = Field1(alias='no-au-peer-set', description='Get the NoAuPeerSet object of an AU')
            state: Optional[State] = Field1(description='Get the state of an AU')
            status: Optional[Status] = Field1(description='Get the status of an AU')
            suspect_urls: Optional[SuspectUrls] = Field1(description='Get the suspect URL versions of an AU')

        class LastUpdateTime(AuthOptions): pass

        class LoadedUrls(AuthOptions): pass

        class Platform(output_options('PlatformConfigurationWsResultOptions', config.PlatformConfigurationWsResult), AuthOptions): pass

        class Section(BaseModel1):

            class Get(IfMatchOptions, OutputOptions, AuthOptions):
                section: str = Field1(description='the name of the section for which the configuration file is requested')

            get: Optional[Get] = Field1(description='Get the named configuration file')

        class Status(output_options('ConfigApiStatusOptions', config.ApiStatus), NodeOptions): pass

        class Url(IfMatchOptions, OutputOptions, AuthOptions):
            url: str = Field1(aliases=['-u'], description='the URL for which the configuration is requested')

        class Users(BaseModel1):

            class Get(UserAccountOptions, AuthOptions): pass

            class Usernames(AuthOptions): pass

            get: Optional[Get] = Field1(description='Get user account details')
            usernames: Optional[Usernames] = Field1(description='Get the usernames configured in the system')

        aus: Optional[Aus] = Field1(description='AU operations')
        last_update_time: Optional[LastUpdateTime] = Field1(alias='last-update-time', description='Get the timestamp when the configuration was last updated')
        loaded_urls: Optional[LoadedUrls] = Field1(alias='loaded-urls', description='Get the URLs from which the cofniguration was loaded')
        platform: Optional[Platform] = Field1(description='Get the platform configuration')
        section: Optional[Section] = Field1(description='Section operations')
        status: Optional[Status] = Field1(description='Get the status of the service')
        url: Optional[Url] = Field1(description='Get the configuration file for a URL')
        users: Optional[Users] = Field1(description='User operations')

    class Crawler(BaseModel1):

        class Crawlers(BaseModel1):

            class Get(output_options('CrawlerConfigOptions', crawler.CrawlerConfig, disambiguate=['crawler-id']), CrawlerIdOptions, AuthOptions): pass

            class GetAll(output_options('CrawlerStatusesOptions', crawler.CrawlerStatuses), AuthOptions): pass

            get: Optional[Get] = Field1(description='Get queued crawl job')
            get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the list of crawl jobs')

        class Crawls(BaseModel1):

            class Get(CrawlStatusOptions, JobOptions, AuthOptions): pass

            class GetAll(CrawlStatusOptions, AuthOptions): pass

            class Urls(BaseModel1):

                class Errors(CrawlUrlInfoOptions, JobOptions, AuthOptions): pass

                class Excluded(CrawlUrlInfoOptions, JobOptions, AuthOptions): pass

                class Fetched(CrawlUrlInfoOptions, JobOptions, AuthOptions): pass

                class MediaTypes(BaseModel1):

                    class Get(CrawlUrlInfoOptions, JobOptions, AuthOptions):
                        media_type: str = Field1(description='the media type (e.g. application/pdf)')

                    #class GetAll(JobOptions, AuthOptions): pass

                    get: Optional[Get] = Field1(description='Get the URLs of a given media type for a crawl')
                    #get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the media types for a crawl')

                class NotModified(CrawlUrlInfoOptions, JobOptions, AuthOptions): pass

                class Parsed(CrawlUrlInfoOptions, JobOptions, AuthOptions): pass

                class Pending(CrawlUrlInfoOptions, JobOptions, AuthOptions): pass

                errors: Optional[Errors] = Field1(description='Get the error URLs for a crawl')
                excluded: Optional[Excluded] = Field1(description='Get the excluded URLs for a crawl')
                fetched: Optional[Fetched] = Field1(description='Get the fetched URLs for a crawl')
                media_types: Optional[MediaTypes] = Field1(alias='media-types', description='Subcommand for media type operations')
                not_modified: Optional[NotModified] = Field1(alias='not-modified', description='Get the not modified URLs for a crawl')
                parsed: Optional[Parsed] = Field1(description='Get the parsed URLs for a crawl')
                pending: Optional[Pending] = Field1(description='Get the pending URLs for a crawl')

            get: Optional[Get] = Field1(description='Get the list of crawls')
            get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the crawl status of a job')
            urls: Optional[Urls] = Field1(description='Subcommand for crawl URL operations')

        class Jobs(BaseModel1):

            class Delete(AuthOptions): pass # FIXME

            class DeleteAll(AuthOptions): pass # FIXME

            class Get(CrawlJobOptions, JobOptions, AuthOptions): pass

            class GetAll(CrawlJobOptions, AuthOptions): pass

            class Request(AuthOptions): pass # FIXME

            delete: Optional[Delete] = Field1(description='Remove or stop a crawl job') # FIXME
            delete_all: Optional[DeleteAll] = Field1(alias='delete-all', description='Delete all of the currently queued and active crawl jobs') # FIXME
            get: Optional[Get] = Field1(description='Get queued poll status')
            get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the list of crawl jobs')
            request: Optional[Request] = Field1(description='Request a crawl as defined by the descriptor') # FIXME

        class Status(output_options('CrawlerApiStatusOptions', crawler.ApiStatus), NodeOptions): pass

        crawlers: Optional[Crawlers] = Field1(description='Subcommand for crawler information operations')
        crawls: Optional[Crawls] = Field1(description='Subcommand for crawl status operations')
        jobs: Optional[Jobs] = Field1(description='Subcommand for crawler job operations')
        status: Optional[Status] = Field1(description='Get the status of the service')

    class Md(BaseModel1):

        class Get(output_options('ItemMetadataOptions', md.ItemMetadata), AuidOptions, AuthOptions): pass

        class Jobs(BaseModel1):

            class Delete(AuthOptions): pass # FIXME

            class DeleteAll(AuthOptions): pass # FIXME

            class Get(MdJobOptions, JobOptions, AuthOptions): pass

            class GetAll(MdJobOptions, AuthOptions): pass

            class Request(AuthOptions): pass # FIXME

            delete: Optional[Delete] = Field1(description='Delete a metadata job') # FIXME
            delete_all: Optional[DeleteAll] = Field1(alias='delete-all', description='Delete all of the currently queued and active metadata jobs') # FIXME
            get: Optional[Get] = Field1(description='Get queued job status')
            get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the list of queued jobs')
            request: Optional[Request] = Field1(description='Request a metadata update operation') # FIXME

        class Query(BaseModel1):

            class Doi(MdUrlInfoOptions, DoiOptions, AuthOptions): pass

            class OpenUrl(MdUrlInfoOptions, OpenUrlOptions, AuthOptions): pass

            doi: Optional[Doi] = Field1(description='Perform a DOI query')
            openurl: Optional[OpenUrl] = Field1(description='Perform an OpenURL query')

        class Status(output_options('MdApiStatusOptions', md.ApiStatus), NodeOptions): pass

        get: Optional[Get] = Field1(description='Get the metadata stored for an AU')
        jobs: Optional[Jobs] = Field1(description='Subcommand for metadata job operations')
        query: Optional[Query] = Field1(description='Subcommand for query operations')
        status: Optional[Status] = Field1(description='Get the status of the service')

    class Poller(BaseModel1):

        class Jobs(BaseModel1):

            class Get(output_options('PollerSummaryOptions', poller.PollerSummary, disambiguate=['poll-key']), JobOptions, AuthOptions): pass

            class Request(AuthOptions): pass # FIXME

            get: Optional[Get] = Field1(description='Get queued poll status')
            request: Optional[Request] = Field1(description='Request to call a poll as the poller') # FIXME

        class Polls(BaseModel1):

            class AsPoller(BaseModel1):

                class Get(output_options('PollerDetailOptions', poller.PollerDetail, disambiguate=['poll-key']), PollKeyOptions, AuthOptions): pass

                class GetAll(output_options('PollerSummaryOptions', poller.PollerSummary, disambiguate=['poll-key']), AuthOptions): pass

                get: Optional[Get] = Field1(description='Get the detailed information about a poll in which a node is the poller')
                get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the list of recent polls in which a node is the poller')

            class AsVoter(BaseModel1):

                class Get(output_options('VoterDetailOptions', poller.VoterDetail, disambiguate=['poll-key']), PollKeyOptions, AuthOptions): pass

                class GetAll(output_options('VoterSummaryOptions', poller.VoterSummary, disambiguate=['poll-key']), AuthOptions): pass

                get: Optional[Get] = Field1(description='Get the detailed information about a poll in which a node is a voter')
                get_all: Optional[GetAll] = Field1(alias='get-all', description='Get the list of recent polls in which a node is a voter')

            class PeerData(PeerIdOptions, AuthOptions): pass

            class Repairs(output_options('RepairDataOptions', poller.RepairData), RepairTypeOptions, PollKeyOptions, AuthOptions): pass

            class Tallies(TallyTypeOptions, PollKeyOptions, AuthOptions): pass

            as_poller: Optional[AsPoller] = Field1(alias='as-poller', description='Subcommand for polls in which a node is the poller')
            as_voter: Optional[AsVoter] = Field1(alias='as-voter', description='Subcommand for polls in which a node is the voter')
            peer_data: Optional[PeerData] = Field1(alias='peer-data', description='Get peer data for a poll')
            repairs: Optional[Repairs] = Field1(description='Get the repairs for a poll')
            tallies: Optional[Tallies] = Field1(description='Get the tallies for a poll')

        class Status(output_options('PollerApiStatusOptions', poller.ApiStatus), NodeOptions): pass

        jobs: Optional[Jobs] = Field1(description='Subcommand for poller job operations')
        polls: Optional[Polls] = Field1(description='Subcommand for poll status operations')
        status: Optional[Status] = Field1(description='Get the status of the service')

    class Repo(BaseModel1):

        class Artifacts(BaseModel1):

            class Delete(UuidOptions, NamespaceOptions, AuthOptions): pass

            class Get(BaseModel1):

                class ByAuid(ArtifactOptions, UncommittedOptions, VersionsOptions, UrlPrefixOptions, AuidOptions, AuthOptions): pass

                class ByUrl(ArtifactOptions, VersionsOptions, UrlPrefixOptions, NamespaceOptions, AuthOptions): pass

                class ByUuid(UuidOptions, AuthOptions):
                    response: Optional[Union[Path, Literal['-']]] = Field1(description='write the response headers to the given file, or "-" for standard output')
                    payload: Optional[Union[Path, Literal['-']]] = Field1(description='write the payload to the given file, or "-" for standard output')

                by_auid: Optional[ByAuid] = Field1(alias='by-auid', description='Get artifacts in an Archival Unit')
                by_url: Optional[ByUrl] = Field1(alias="by-url", description="Returns all artifacts that match a given URL or URL prefix and/or version")
                by_uuid: Optional[ByUuid] = Field1(alias="by-uuid", description="Gets artifacts and artifact metadata")

            class Update(UuidOptions, NamespaceOptions, AuthOptions):
                commit: bool = Field1(description='Whether the artifact should be marked as committed or not committed')

            delete: Optional[Delete] = Field1(description='Deletes an artifact')
            get: Optional[Get] = Field1(description='Gets one or more artifacts')
            update: Optional[Update] = Field1(description='Updates an artifact')

        class Aus(BaseModel1):

            class Auids(NamespaceOptions, AuthOptions): pass

            class Size(output_options('AuSizeOptions', rs.AuSize), AuidOptions, AuthOptions): pass

            auids: Optional[Auids] = Field1(description='Get Archival Unit IDs (AUIDs) in a namespace')
            size: Optional[Size] = Field1(description='Get the size of Archival Unit artifacts in a namespace')

        class ChecksumAlgorithms(AuthOptions): pass

        class Info(output_options('RepositoryInfoOptions', rs.RepositoryInfo), AuthOptions): pass

        class Namespaces(AuthOptions): pass

        class Status(output_options('RsApiStatusOptions', rs.ApiStatus), NodeOptions): pass

        class StorageInfo(AuthOptions): pass

        artifacts: Optional[Artifacts] = Field1(description="LOCKSS Repository Service API artifacts commands")
        aus: Optional[Aus] = Field1(description='LOCKSS Repository Service API archival unit (AU) commands')
        checksum_algorithms: Optional[ChecksumAlgorithms] = Field1(alias='checksum-algorithms', description='Get the supported checksum algorithms')
        info: Optional[Info] = Field1(description='Get repository information')
        namespaces: Optional[Namespaces] = Field1(description='Get namespaces of the committed artifacts in the repository')
        status: Optional[Status] = Field1(description="Get the status of the service")
        storage_info: Optional[StorageInfo] = Field1(alias='storage-info', description="Get repository storage information")

    config: Optional[Config] = Field1(description='Subcommand for Configuration Service operations')
    copyright: Optional[BaseModel1] = Field1(description=COPYRIGHT_DESCRIPTION)
    crawler: Optional[Crawler] = Field1(description='Subcommand for Crawler Service operations')
    license: Optional[BaseModel1] = Field1(description=LICENSE_DESCRIPTION)
    md: Optional[Md] = Field1(description='Subcommand for Metadata Service operations')
    poller: Optional[Poller] = Field1(description='Subcommand for Poller Service operations')
    repo: Optional[Repo] = Field1(description='Subcommand for Repository Service operations')
    version: Optional[BaseModel1] = Field1(description=VERSION_DESCRIPTION)


class LockssApiCli(BaseCli[LockssApi]):

    def __init__(self):
        """
        Constructs a new ``DebugPanelCli`` instance.
        """
        super().__init__(model=LockssApi,
                         prog='lockssapi',
                         description='LOCKSS Python client')

    def _config_aus_agreements(self, cmd: LockssApi.Config.Aus.Agreements) -> None:
        print(config_get_au_agreements(cmd.make_node(),
                                       cmd.auid).to_dict())

    def _config_aus_configuration_get(self, cmd: LockssApi.Config.Aus.Configuration.Get) -> None:
        cmd.display(config_get_au_config(cmd.make_node(),
                                         cmd.auid))

    def _config_aus_configuration_get_all(self, cmd: LockssApi.Config.Aus.Configuration.GetAll) -> None:
        cmd.display(config_get_au_configs(cmd.make_node()))

    def _config_aus_no_au_peer_set(self, cmd: LockssApi.Config.Aus.NoAuPeerSet) -> None:
        cmd.display(config_get_no_au_peer_set(cmd.make_node(),
                                              cmd.auid))

    def _config_aus_state(self, cmd: LockssApi.Config.Aus.State) -> None:
        cmd.display(config_get_au_state(cmd.make_node(),
                                        cmd.auid))

    def _config_aus_status(self, cmd: LockssApi.Config.Aus.Status) -> None:
        cmd.display(config_get_au_status(cmd.make_node(),
                                         cmd.auid))

    def _config_aus_suspect_urls(self, cmd: LockssApi.Config.Aus.SuspectUrls) -> None:
        cmd.display(config_get_au_suspect_url_versions(cmd.make_node(),
                                                       cmd.auid).suspect_versions)

    def _config_last_update_time(self, cmd: LockssApi.Config.LastUpdateTime) -> None:
        print(config_last_update_time(cmd.make_node()))

    def _config_loaded_urls(self, cmd: LockssApi.Config.LoadedUrls) -> None:
        for url in config_get_loaded_urls(cmd.make_node()):
            print(url)

    def _config_platform(self, cmd: LockssApi.Config.Platform) -> None:
        cmd.display(config_get_platform_config(cmd.make_node()))

    def _config_section_get(self, cmd: LockssApi.Config.Section.Get) -> None:
        mp = config_get_section(cmd.make_node(),
                                cmd.section,
                                if_match=cmd.if_match,
                                if_modified_since=cmd.if_modified_since,
                                if_none_match=cmd.if_none_match,
                                if_unmodified_since=cmd.if_unmodified_since)
        part = None
        try:
            part = mp.get('configFile')
            if cmd.output:
                part.save_as(cmd.output)
            else:
                for line in TextIOWrapper(part.file):
                    print(line, end='')
        finally:
            if part:
                part.close()

    def _config_status(self, cmd: LockssApi.Config.Status) -> None:
        cmd.display(config_get_status(cmd.make_node()))

    def _config_url(self, cmd: LockssApi.Config.Url) -> None:
        mp = config_get_url(cmd.make_node(),
                            cmd.url,
                            if_match=cmd.if_match,
                            if_modified_since=cmd.if_modified_since,
                            if_none_match=cmd.if_none_match,
                            if_unmodified_since=cmd.if_unmodified_since)
        part = None
        try:
            part = mp.get('configFile')
            if cmd.output:
                part.save_as(cmd.output)
            else:
                for line in TextIOWrapper(part.file):
                    print(line, end='')
        finally:
            if part:
                part.close()

    def _config_users_get(self, cmd: LockssApi.Config.Users.Get) -> None:
        print(config_get_user_account(cmd.make_node(),
                                      cmd.user_account))

    def _config_users_usernames(self, cmd: LockssApi.Config.Users.Usernames) -> None:
        for username in sorted(config_get_usernames(cmd.make_node())):
            print(username)

    def _copyright(self, cmd: BaseModel1) -> None:
        self._parser.exit(0, __copyright__)

    def _crawler_crawlers_get(self, cmd: LockssApi.Crawler.Crawlers.Get) -> None:
        cmd.display(crawler_get_crawler(cmd.make_node(),
                                        cmd.crawler_id))

    def _crawler_crawlers_get_all(self, cmd: LockssApi.Crawler.Crawlers.GetAll) -> None:
        cmd.display(crawler_get_crawlers(cmd.make_node()))

    def _crawler_crawls_urls_errors(self, cmd: LockssApi.Crawler.Crawls.Urls.Errors) -> None:
        cmd.display(crawler_get_crawl_errors(cmd.make_node(),
                                             cmd.job))

    def _crawler_crawls_urls_excluded(self, cmd: LockssApi.Crawler.Crawls.Urls.Excluded) -> None:
        cmd.display(crawler_get_crawl_excluded(cmd.make_node(),
                                               cmd.job))

    def _crawler_crawls_urls_fetched(self, cmd: LockssApi.Crawler.Crawls.Urls.Fetched) -> None:
        cmd.display(crawler_get_crawl_fetched(cmd.make_node(),
                                              cmd.job))

    def _crawler_crawls_get(self, cmd: LockssApi.Crawler.Crawls.Get) -> None:
        cmd.display(crawler_get_crawl(cmd.make_node(),
                                      cmd.job))

    def _crawler_crawls_get_all(self, cmd: LockssApi.Crawler.Crawls.GetAll) -> None:
        cmd.display(crawler_get_crawls(cmd.make_node()))

    def _crawler_crawls_urls_media_types_get(self, cmd: LockssApi.Crawler.Crawls.Urls.MediaTypes.Get) -> None:
        cmd.display(crawler_get_crawl_by_media_type(cmd.make_node(),
                                                    cmd.job,
                                                    cmd.media_type))

    def _crawler_crawls_urls_not_modified(self, cmd: LockssApi.Crawler.Crawls.Urls.NotModified) -> None:
        cmd.display(crawler_get_crawl_not_modified(cmd.make_node(),
                                                   cmd.job))

    def _crawler_crawls_urls_parsed(self, cmd: LockssApi.Crawler.Crawls.Urls.Parsed) -> None:
        cmd.display(crawler_get_crawl_parsed(cmd.make_node(),
                                             cmd.job))

    def _crawler_crawls_urls_pending(self, cmd: LockssApi.Crawler.Crawls.Urls.Pending) -> None:
        cmd.display(crawler_get_crawl_pending(cmd.make_node(),
                                              cmd.job))

    def _crawler_jobs_get(self, cmd: LockssApi.Crawler.Jobs.Get) -> None:
        cmd.display(crawler_get_job(cmd.make_node(),
                                    cmd.job))

    def _crawler_jobs_get_all(self, cmd: LockssApi.Crawler.Jobs.GetAll) -> None:
        cmd.display(crawler_get_jobs(cmd.make_node()))

    def _crawler_status(self, cmd: LockssApi.Crawler.Status) -> None:
        cmd.display(crawler_get_status(cmd.make_node()))

    def _license(self, cmd: BaseModel1) -> None:
        self._parser.exit(0, __license__)

    def _md_get(self, cmd: LockssApi.Md.Get) -> None:
        cmd.display(md_get_metadata(cmd.make_node(),
                                    cmd.auid))

    def _md_jobs_get(self, cmd: LockssApi.Md.Jobs.Get) -> None:
        cmd.display(md_get_job(cmd.make_node(),
                               cmd.job))

    def _md_jobs_get_all(self, cmd: LockssApi.Md.Jobs.GetAll) -> None:
        cmd.display(md_get_jobs(cmd.make_node()))

    def _md_query_doi(self, cmd: LockssApi.Md.Query.Doi) -> None:
        cmd.display(md_doi_query(cmd.make_node(),
                                 cmd.doi))

    def _md_query_openurl(self, cmd: LockssApi.Md.Query.OpenUrl) -> None:
        cmd.display(md_openurl_query(cmd.make_node(),
                                     cmd.params))

    def _md_status(self, cmd: LockssApi.Md.Status) -> None:
        cmd.display(md_get_status(cmd.make_node()))

    def _poller_jobs_get(self, cmd: LockssApi.Poller.Jobs.Get) -> None:
        cmd.display(poller_get_poll_status(cmd.make_node(),
                                           cmd.job))

    def _poller_polls_as_poller_get(self, cmd: LockssApi.Poller.Polls.AsPoller.Get) -> None:
        cmd.display(poller_get_poller_poll(cmd.make_node(),
                                           cmd.poll_key))

    def _poller_polls_as_poller_get_all(self, cmd: LockssApi.Poller.Polls.AsPoller.GetAll) -> None:
        cmd.display(poller_get_poller_polls(cmd.make_node()))

    def _poller_polls_as_voter_get(self, cmd: LockssApi.Poller.Polls.AsVoter.Get) -> None:
        cmd.display(poller_get_voter_poll(cmd.make_node(),
                                          cmd.poll_key))

    def _poller_polls_as_voter_get_all(self, cmd: LockssApi.Poller.Polls.AsVoter.GetAll) -> None:
        cmd.display(poller_get_voter_polls(cmd.make_node()))

    def _poller_polls_peer_data(self, cmd: LockssApi.Poller.Polls.PeerData) -> None:
        for url in poller_get_peer_data(cmd.make_node(),
                                        cmd.poll_key,
                                        cmd.peer_id,
                                        cmd.get_voter_urls_enum()):
            print(url)

    def _poller_polls_repairs(self, cmd: LockssApi.Poller.Polls.Repairs) -> None:
        cmd.display(poller_get_repair_data(cmd.make_node(),
                                           cmd.poll_key,
                                           cmd.get_repair_type_enum()))

    def _poller_polls_tallies(self, cmd: LockssApi.Poller.Polls.Tallies) -> None:
        for url in poller_get_tally_urls(cmd.make_node(),
                                         cmd.poll_key,
                                         cmd.get_tally_type_enum()):
            print(url)

    def _poller_status(self, cmd: LockssApi.Poller.Status) -> None:
        cmd.display(poller_get_status(cmd.make_node()))

    def _repo_artifacts_delete(self, cmd: LockssApi.Repo.Artifacts.Delete) -> None:
        repo_delete_artifact(cmd.make_node(),
                             cmd.uuid,
                             namespace=cmd.get_namespace(_param_default(_RS, '/artifacts/{uuid}', 'delete', 'namespace')))
        print(cmd.uuid)

    def _repo_artifacts_get_by_auid(self, cmd: LockssApi.Repo.Artifacts.Get.ByAuid) -> None:
        cmd.display(repo_get_artifacts_by_auid(cmd.make_node(),
                                               cmd.auid,
                                               url=cmd.url,
                                               url_prefix=cmd.url_prefix,
                                               namespace=cmd.get_namespace(_param_default(_RS, '/aus/{auid}/artifacts', 'get', 'namespace')),
                                               versions=cmd.get_versions_enum(rs.VersionsEnum.LATEST),
                                               include_uncommitted=cmd.uncommitted))

    def _repo_artifacts_by_url(self, cmd: LockssApi.Repo.Artifacts.Get.ByUrl) -> None:
        cmd.display(repo_get_artifacts_by_url(cmd.make_node(),
                                              url=cmd.url,
                                              url_prefix=cmd.url_prefix,
                                              namespace=cmd.get_namespace(_param_default(_RS, '/artifacts', 'get', 'namespace')),
                                              versions=cmd.get_versions_enum(rs.VersionsEnum.LATEST)))

    def _repo_artifacts_get_by_uuid(self, cmd: LockssApi.Repo.Artifacts.Get.ByUuid) -> None:
        mp = repo_get_artifact_by_uuid(cmd.make_node(),
                                       cmd.uuid,
                                       namespace=_param_default(_RS, '/artifacts/{uuid}', 'get', 'namespace'),
                                       include_content=rs.IncludeContentEnum.ALWAYS if cmd.payload else rs.IncludeContentEnum.NEVER)
        print(mp.get('artifactProps').value)
        for path, part_name in ((cmd.response, 'httpResponseHeader'), (cmd.payload, 'payload')):
            if path is None:
                continue
            part = None
            try:
                part = mp.get(part_name)
                if path == '-':
                    print()
                    while len((bytez := part.file.read(1024))) > 0:
                        sys.stdout.write(bytez)
                else:
                    part.save_as(path)
            finally:
                if part:
                    part.close()

    def _repo_aus_auids(self, cmd: LockssApi.Repo.Aus.Auids) -> None:
        for auid in sorted(repo_get_auids(cmd.make_node())):
            print(auid)

    def _repo_aus_size(self, cmd: LockssApi.Repo.Aus.Size) -> None:
        cmd.display(repo_get_au_size(cmd.make_node(),
                                     cmd.auid,
                                     namespace=cmd.get_namespace(_param_default(_RS, '/aus/{auid}/size', 'get', 'namespace'))))

    def _repo_checksum_algorithms(self, cmd: LockssApi.Repo.ChecksumAlgorithms) -> None:
        for checksum_algorithm in sorted(repo_get_checksum_algorithms(cmd.make_node())):
            print(checksum_algorithm)

    def _repo_info(self, cmd: LockssApi.Repo.Info) -> None:
        cmd.display(repo_get_info(cmd.make_node()))

    def _repo_namespaces(self, cmd: LockssApi.Repo.Namespaces) -> None:
        for namespace in sorted(repo_get_namespaces(cmd.make_node())):
            print(namespace)

    def _repo_status(self, cmd: LockssApi.Repo.Status) -> None:
        cmd.display(repo_get_status(cmd.make_node()))

    def _repo_storage_info(self, cmd: LockssApi.Repo.StorageInfo) -> None:
        print(repo_get_storage_info(cmd.make_node()).to_dict())

    def _version(self, cmd: BaseModel1) -> None:
        self._parser.exit(0, __version__)
'''

@dataclass(kw_only=True)
class _Opts(_FormatOpts):
    node: Optional[str] = None
    repository_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = field(default=None, repr=False)


class _LockssApiCli(object):

    def __init__(self, ctx: ExtraContext):
        super().__init__()
        self._ctx: ExtraContext = ctx
        self._opts: Optional[_Opts] = None
        self._node: Optional[Node] = None

    def initialize(self, opts: _Opts) -> None:
        self._opts = opts

    def initialize_repo_operation(self):
        opts = self._opts
        self._node = Node(opts.node, username=opts.username, password=opts.password, rs_port=opts.repository_port)

    def repo_status(self):
        self.initialize_repo_operation()
        display(self._opts, repo_get_status(self._node))


_node_options = (
    option('--node', '--host', '-n', '-H', metavar='HOST', required=True, help='Set the host of the node to be processed to HOST.'),
    option('--username', '-U', metavar='USER', show_default='interactive prompt', help='Set the API username to USER.', prompt='API username'),
    password_option('--password', '-P', metavar='PASS', show_default='interactive prompt', help='Set the API password to PASS.', prompt='API password', confirmation_prompt=False)
)


def _make_node_option_group(long: str,
                            short: str,
                            default: int,
                            service: str):
    return option_group('Node options',
                        *_node_options,
                        option(f'--{long}-port', f'-{short}', metavar='PORT', type=NonNegativeInt, default=default, help=f'Set the {service} Service API port to PORT'))


_repo_node_option_group = _make_node_option_group('repository', 'R', RS_DEFAULT_PORT, 'Repository')


@group('lockssapi', params=None, context_settings=make_extra_context_settings())
@color_option
@show_params_option
@pass_context
def _lockssapi(ctx: ExtraContext, **kwargs):
    ctx.obj = _LockssApiCli(ctx)


@_lockssapi.command('copyright', help='Show the copyright then exit.')
def _copyright() -> None:
    echo(__copyright__)


@_lockssapi.command('license', help='Show the software license then exit.')
def license() -> None:
    echo(__license__)


@_lockssapi.group('repo', help='Subcommand for Repository Service operations.')
@pass_obj
def _repo(cli: _LockssApiCli, **kwargs):
    pass


@_repo.command('status', help='Get the status of the Repository Service.')
@_repo_node_option_group
@make_output_option_group(rs.ApiStatus)
@pass_obj
def _repo_status(cli: _LockssApiCli, **kwargs) -> None:
    cli.initialize(_Opts(**kwargs))
    cli.repo_status()


@_lockssapi.command('version', help='Show the version number then exit.')
def version() -> None:
    echo(__version__)


def main() -> None:
    """
    Entry point for the lockssapi command line tool.
    """
    #LockssApiCli().run()
    _lockssapi()


if __name__ == '__main__':
    main()
