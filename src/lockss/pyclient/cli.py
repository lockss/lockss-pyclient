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

from pathlib import Path
from typing import Literal
import sys

from lockss.pybasic.cliutil import BaseCli, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, VERSION_DESCRIPTION
from pydantic.v1 import BaseModel as BaseModel1, Field as Field1, NonNegativeInt as NonNegativeInt1, root_validator as root_validator1

from .output import create_output_options
from . import *
from . import __copyright__, __license__, __version__
from ._internal_common import _param_default, _RS
from ._internal_rs import repo_delete_artifact
from . import rs


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
    auid: str = Field1(aliases=["-a"], description="Archival Unit ID (AUID)")


class UrlOptions(BaseModel1):
    url: Optional[str] = Field1(aliases=["-u"], description="URL")


class UrlPrefixOptions(UrlOptions):
    url_prefix: Optional[str] = Field1(aliases=["-p"], description="URL prefix")

    @root_validator1
    def _validate_exactly_one(cls, values):
        attrs = ('url', 'url_prefix')
        if len([attr for attr in attrs if values.get(attr)]) != 1:
            raise ValueError('Expected exactly one of {", ".join(f"--{hattr}" for hattr in [attr.replace("_", "-") for attr in attrs])}')
        return values


class UuidOptions(NamespaceOptions):
    uuid: str = Field1(aliases=["-w"], description="Artifact identifier")


class UncommittedOptions(BaseModel1):
    uncommitted: bool = Field1(False, description='include uncommitted artifacts in results')


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


ArtifactOptions = create_output_options('ArtifactOptions',
                                        rs.Artifact,
                                        disambiguate=['auid', 'namespace'])


AuSizeOptions = create_output_options('AuSizeOptions', rs.AuSize)


RepositoryInfoOptions = create_output_options('RepositoryInfoOptions', rs.RepositoryInfo)


RsApiStatusOptions = create_output_options('RsApiStatusOptions', rs.ApiStatus)


class LockssApi(BaseModel1):

    class Repo(BaseModel1):

        class Artifacts(BaseModel1):

            class Get(BaseModel1):

                class ByAuid(ArtifactOptions, UncommittedOptions, VersionsOptions, UrlPrefixOptions, AuidOptions, NamespaceOptions, AuthOptions): pass

                class ByUrl(ArtifactOptions, VersionsOptions, UrlPrefixOptions, NamespaceOptions, AuthOptions): pass

                class ByUuid(UuidOptions, AuthOptions):
                    response: Optional[Union[Path, Literal['-']]] = Field1(description='Store the response headers in the given file, or "-" for standard output')
                    payload: Optional[Union[Path, Literal['-']]] = Field1(description='Store the payload in the given file, or "-" for standard output')

                by_auid: Optional[ByAuid] = Field1(alias='by-auid', description='Get artifacts in an Archival Unit')
                by_url: Optional[ByUrl] = Field1(alias="by-url", description="Returns all artifacts that match a given URL or URL prefix and/or version")
                by_uuid: Optional[ByUuid] = Field1(alias="by-uuid", description="Gets artifacts and artifact metadata")

            class Delete(UuidOptions, NamespaceOptions, AuthOptions): pass

            class Update(UuidOptions, NamespaceOptions, AuthOptions):
                commit: bool = Field1(description='Whether the artifact should be marked as committed or not committed')

            delete: Optional[Delete] = Field1(description='Deletes an artifact')
            get: Optional[Get] = Field1(description='Gets one or more artifacts')
            update: Optional[Update] = Field1(description='Updates an artifact')

        class Aus(BaseModel1):

            class Auids(NamespaceOptions, AuthOptions): pass

            class Size(AuSizeOptions, AuidOptions, AuthOptions): pass

            auids: Optional[Auids] = Field1(description='Get Archival Unit IDs (AUIDs) in a namespace')
            size: Optional[Size] = Field1(description='Get the size of Archival Unit artifacts in a namespace')

        class ChecksumAlgorithms(AuthOptions): pass

        class Info(RepositoryInfoOptions, AuthOptions): pass

        class Namespaces(AuthOptions): pass

        class Status(RsApiStatusOptions, NodeOptions): pass

        class StorageInfo(AuthOptions): pass

        artifacts: Optional[Artifacts] = Field1(description="LOCKSS Repository Service API artifacts commands")
        aus: Optional[Aus] = Field1(description='LOCKSS Repository Service API archival unit (AU) commands')
        checksum_algorithms: Optional[ChecksumAlgorithms] = Field1(alias='checksum-algorithms', description='Get the supported checksum algorithms')
        info: Optional[Info] = Field1(description='Get repository information')
        namespaces: Optional[Namespaces] = Field1(description='Get namespaces of the committed artifacts in the repository')
        status: Optional[Status] = Field1(description="Get the status of the service")
        storage_info: Optional[StorageInfo] = Field1(alias='storage-info', description="Get repository storage information")

    copyright: Optional[BaseModel1] = Field1(description=COPYRIGHT_DESCRIPTION)
    license: Optional[BaseModel1] = Field1(description=LICENSE_DESCRIPTION)
    repo: Optional[Repo] = Field1(description='Repository Service operations')
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
                    while len((byt := part.file.read(1024))) > 0:
                        sys.stdout.write(byt)
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


def main() -> None:
    """
    Entry point for the lockssapi command line tool.
    """
    LockssApiCli().run()


if __name__ == '__main__':
    main()
