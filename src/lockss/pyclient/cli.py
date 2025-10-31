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

from typing import Optional
import inspect

from io import BytesIO
from multipart import MultipartParser
from pydantic.v1 import BaseModel as BaseModel1, Field as Field1, NonNegativeInt as NonNegativeInt1

from lockss.pybasic.cliutil import BaseCli, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, VERSION_DESCRIPTION
from lockss.pybasic.errorutil import InternalError

from . import __copyright__, __license__, __version__
from .output import create_output_options
from lockss.pyclient import rs


RS_PORT: NonNegativeInt1 = NonNegativeInt1(24610)
RS_DESCRIPTION="LOCKSS Repository Service commands"


class NodeOptions(BaseModel1):
    host: str = Field1(aliases=["-H"], description="The IP address or FQDN of the LOCKSS node, optionally followed by a colon and a port number")

    def make_conf(self, default_port: NonNegativeInt1) -> rs.Configuration:
        conf = rs.Configuration()
        h, _, p = self.host.partition(':')
        conf.host = f'http://{self.host}{"" if p else f":{default_port}"}'
        return conf


class AuthOptions(NodeOptions):
    username: str = Field1(aliases=["-U"], description="LOCKSS API username")
    password: str = Field1(aliases=["-P"], description="LOCKSS API password")

    def make_conf(self, default_port: NonNegativeInt1) -> rs.Configuration:
        conf = super().make_conf(default_port)
        conf.username = self.username
        conf.password = self.password
        return conf


class NamespaceOptions(BaseModel1):
    namespace: Optional[str] = Field1(inspect.getfullargspec(rs.Artifact.__init__).defaults[1],
                                      aliases=["-n"],
                                      description="LOCKSS namespace")


class AuidOptions(NamespaceOptions):
    auid: str = Field1(aliases=["-a"], description="Archival Unit ID")


class UrlOptions(BaseModel1):
    url: Optional[str] = Field1(aliases=["-u"], description="URL")


class UrlPrefixOptions(UrlOptions):
    url_prefix: Optional[str] = Field1(aliases=["-p"], description="URL prefix")


class UuidOptions(NamespaceOptions):
    uuid: str = Field1(aliases=["-w"], description="Identifier of the artifact")


class IncludeContentOptions(BaseModel1):
    always: Optional[bool] = Field1(description='Always include the content in the multipart response')
    if_small: Optional[bool] = Field1(description='Include the content in the multipart response if it is relatively small')
    never: Optional[bool] = Field1(description='Never include the content in the multipart response')


RepoAusSizeOutputOptions = create_output_options('RsAusSizeOutputOptions', rs.AuSize)


RepoInfoOptions = create_output_options('RsRepoRepoInfoOptions', rs.RepositoryInfo)


RepoStatusOutputOptions = create_output_options('RsStatusOutputOptions', rs.ApiStatus)


class LockssApi(BaseModel1):

    class Repo(BaseModel1):

        class Artifacts(BaseModel1):

            class ByAuid(AuidOptions, AuthOptions): pass

            class ByUrl(UrlPrefixOptions, NamespaceOptions, AuthOptions): pass

            class ByUuid(IncludeContentOptions, UuidOptions, AuthOptions): pass

            by_auid: Optional[ByAuid] = Field1(alias='by-auid', description='Get artifacts in an Archival Unit')
            by_url: Optional[ByUrl] = Field1(alias="by-url", description="Returns all artifacts that match a given URL or URL prefix and/or version")
            by_uuid: Optional[ByUuid] = Field1(alias="by-uuid", description="Get artifact and metadata")

        class Aus(BaseModel1):

            class Auids(NamespaceOptions, AuthOptions): pass

            class Size(RepoAusSizeOutputOptions, AuidOptions, AuthOptions): pass

            auids: Optional[Auids] = Field1(description='Get Archival Unit IDs (AUIDs) in a namespace')
            size: Optional[Size] = Field1(description='Get the size of Archival Unit artifacts in a namespace')

        class ChecksumAlgorithms(AuthOptions): pass

        class Info(RepoInfoOptions, AuthOptions): pass

        class Namespaces(AuthOptions): pass

        class Status(RepoStatusOutputOptions, NodeOptions): pass

        class Storage(BaseModel1): pass # FIXME

        artifacts: Optional[Artifacts] = Field1(description="LOCKSS Repository Service API artifacts commands")
        aus: Optional[Aus] = Field1(description='LOCKSS Repository Service API archival unit (AU) commands')
        checksum_algorithms: Optional[ChecksumAlgorithms] = Field1(alias='checksum-algorithms', description='Get the supported checksum algorithms')
        info: Optional[Info] = Field1(description='Get repository information')
        namespaces: Optional[Namespaces] = Field1(description='Get namespaces of the committed artifacts in the repository')
        status: Optional[Status] = Field1(description="Get the status of the service")
        storage: Optional[Storage] = Field1(description="Get repository storage information")

    copyright: Optional[BaseModel1] = Field1(description=COPYRIGHT_DESCRIPTION)
    license: Optional[BaseModel1] = Field1(description=LICENSE_DESCRIPTION)
    repo: Optional[Repo] = Field1(description=RS_DESCRIPTION)
    version: Optional[BaseModel1] = Field1(description=VERSION_DESCRIPTION)


class LockssApiCli(BaseCli[LockssApi]):

    def __init__(self):
        """
        Constructs a new ``DebugPanelCli`` instance.
        """
        super().__init__(model=LockssApi,
                         prog='lockssapi',
                         description='LOCKSS Python client')

    def _copyright(self, cmd: BaseModel1) -> None:
        self._parser.exit(0, __copyright__)

    def _license(self, cmd: BaseModel1) -> None:
        self._parser.exit(0, __license__)

    def _repo_artifacts_by_auid(self, cmd: LockssApi.Repo.Artifacts.ByAuid) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.ArtifactsApi(api_client)
        results = []
        token = None
        while True:
            kw = {}
            if token:
                kw['continuation_token'] = token
            api_response: rs.ArtifactPageInfo = api_instance.get_artifacts(cmd.auid,
                                                                           namespace=cmd.namespace,
                                                                           limit=100,
                                                                           **kw)
            results.extend(api_response.artifacts)
            token = api_response.page_info.continuation_token
            if token is None:
                break
        for result in results:
            print(result)

    def _repo_artifacts_by_url(self, cmd: LockssApi.Repo.Artifacts.ByUrl) -> None:
        if cmd.url and cmd.url_prefix:
            self._parser.error('--url/-u and --url-prefix/-p are mutually exclusive')
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.ArtifactsApi(api_client)
        kw = {}
        if cmd.url:
            kw['url'] = cmd.url
        if cmd.url_prefix:
            kw['url_prefix'] = cmd.url_prefix
        token = None
        results = []
        while True:
            if token:
                kw['continuation_token'] = token
            else:
                kw.pop('continuation_token', None)
            api_response: rs.ArtifactPageInfo = api_instance.get_artifacts_from_all_aus(namespace=cmd.namespace,
                                                                                        limit=100,
                                                                                        **kw)
            results.extend(api_response.artifacts)
            token = api_response.page_info.continuation_token
            if token is None:
                break
        for result in results:
            print(result)

    def _repo_artifacts_by_uuid(self, cmd: LockssApi.Repo.Artifacts.ByUuid) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.ArtifactsApi(api_client)
        api_response = api_instance.get_artifact_data_by_multipart(cmd.uuid,
                                                                   namespace=cmd.namespace,
                                                                   include_content='NEVER' if cmd.never else 'IF_SMALL' if cmd.if_small else 'ALWAYS')
        # api_response is of type str but seems to be a repr() string!
        byte_input = eval(api_response)
        boundary = byte_input.partition(b'\r\n')[0].partition(b'--')[2]
        parser = MultipartParser(BytesIO(byte_input), boundary)
        for part in parser:
            print(f'{part.name} {part.size}')

    def _repo_aus_auids(self, cmd: LockssApi.Repo.Aus.Auids) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.AusApi(api_client)
        results = []
        token = None
        while True:
            kw = {}
            if token:
                kw['continuation_token'] = token
            api_response: rs.AuidPageInfo = api_instance.get_aus(namespace=cmd.namespace,
                                                                 limit=100,
                                                                 **kw)
            results.extend(api_response.auids)
            token = api_response.page_info.continuation_token
            if token is None:
                break
        for auid in results:
            print(auid)

    def _repo_aus_size(self, cmd: LockssApi.Repo.Aus.Size) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.AusApi(api_client)
        api_response: list[str] = api_instance.get_artifacts_size(namespace=cmd.namespace,
                                                                  auid=cmd.auid)
        print(api_response)

    def _repo_checksum_algorithms(self, cmd: LockssApi.Repo.ChecksumAlgorithms) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.RepoApi(api_client)
        api_response: list[str] = api_instance.get_supported_checksum_algorithms()
        for algorithm in sorted(api_response, key=lambda s: s.lower()):
            print(algorithm)

    def _repo_info(self, cmd: LockssApi.Repo.Info) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.RepoApi(api_client)
        api_response: rs.RepositoryInfo = api_instance.get_repository_information()
        cmd.display(api_response)

    def _repo_namespaces(self, cmd: LockssApi.Repo.Namespaces) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.RepoApi(api_client)
        api_response: list[str] = api_instance.get_namespaces()
        for namespace in sorted(api_response):
            print(namespace)

    def _repo_status(self, cmd: LockssApi.Repo.Status) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf)
        api_instance = rs.StatusApi(api_client)
        api_response: rs.ApiStatus = api_instance.get_status()
        cmd.display(api_response)

    def _version(self, cmd: BaseModel1) -> None:
        self._parser.exit(0, __version__)


def main() -> None:
    """
    Entry point for the lockssapi command line tool.
    """
    LockssApiCli().run()


if __name__ == '__main__':
    main()
