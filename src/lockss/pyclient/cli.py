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

from pydantic.v1 import BaseModel, Field, NonNegativeInt

from lockss.pybasic.cliutil import BaseCli, StringCommand, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, \
    VERSION_DESCRIPTION
from lockss.pybasic.errorutil import InternalError

from . import __copyright__, __license__, __version__
from .output import create_output_options
from ..pyclient import rs


RS_PORT: NonNegativeInt = NonNegativeInt(24610)
RS_DESCRIPTION="LOCKSS Repository Service commands"


class NodeOptions(BaseModel):
    host: str = Field(aliases=["-H"], description="The IP address or FQDN of the LOCKSS node")
    port: Optional[NonNegativeInt] = Field(aliases=["-P"], description="LOCKSS Service API port")

    def make_conf(self, default_port: NonNegativeInt) -> rs.Configuration:
        conf = rs.Configuration()
        conf.host = f'http://{self.host}:{self.port or default_port}'
        return conf


class AuthOptions(NodeOptions):
    username: str = Field(aliases=["-u"], description="LOCKSS API username")
    password: str = Field(aliases=["-p"], description="LOCKSS API password")

    def make_conf(self, default_port: NonNegativeInt) -> rs.Configuration:
        conf = super().make_conf(default_port)
        conf.username = self.username
        conf.password = self.password
        return conf


class AuidOptions(BaseModel):
    namespace: Optional[str] = Field(
        inspect.getfullargspec(rs.Artifact.__init__).defaults[2],
        aliases=["-n"],
        description="LOCKSS namespace")
    auid: str = Field(aliases=["-a"], description="Archival Unit ID")


RsRepoRepoInfoOptions = create_output_options('RsRepoRepoInfoOptions', rs.RepositoryInfo)

RsStatusOutputOptions = create_output_options('RsStatusOutputOptions', rs.ApiStatus)


class LockssApi(BaseModel):

    class Rs(BaseModel):

        class Artifacts(BaseModel):

            class GetArtifacts(AuidOptions, AuthOptions): pass

            get_artifacts: Optional[GetArtifacts] = Field(alias="get-artifacts", description="Get a list of all artifacts in a namespace and Archival Unit")

        class Repo(BaseModel):

            class RepoInfo(RsRepoRepoInfoOptions, AuthOptions): pass

            repo_info: Optional[RepoInfo] = Field(alias='repo-info', description='Get properties of the repository')

        class Status(RsStatusOutputOptions, NodeOptions): pass

        artifacts: Optional[Artifacts] = Field(description="LOCKSS Repository Service API artifacts commands")
        repo: Optional[Repo] = Field(description='LOCKSS Repository Service API repo commands')
        status: Optional[Status] = Field(description="LOCKSS Repository Service API status commands")

    copyright: Optional[StringCommand.type(__copyright__)] = Field(description=COPYRIGHT_DESCRIPTION)
    license: Optional[StringCommand.type(__license__)] = Field(description=LICENSE_DESCRIPTION)
    version: Optional[StringCommand.type(__version__)] = Field(description=VERSION_DESCRIPTION)
    rs: Optional[Rs] = Field(description=RS_DESCRIPTION)


class LockssApiCli(BaseCli[LockssApi]):
    def __init__(self):
        """
        Constructs a new ``DebugPanelCli`` instance.
        """
        super().__init__(model=LockssApi,
                         prog='lockssapi',
                         description='LOCKSS Python client')

    def _do_string_command(self, cmd: StringCommand) -> None:
        """
        Performs one string command.

        :param cmd: A ``StringCommand`` model.
        :type auid_command: StringCommand
        """
        cmd()

    def _copyright(self, cmd: StringCommand) -> None:
        self._do_string_command(cmd)

    def _license(self, cmd: StringCommand) -> None:
        self._do_string_command(cmd)

    def _rs_artifacts_get_artifacts(self, cmd: LockssApi.Rs.Artifacts.GetArtifacts) -> None:
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
        print(results)

    def _rs_repo_repo_info(self, cmd: LockssApi.Rs.Repo.RepoInfo) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = rs.RepoApi(api_client)
        api_response: rs.RepositoryInfo = api_instance.get_repository_information()
        cmd.display(api_response)

    def _rs_status(self, cmd: LockssApi.Rs.Status) -> None:
        conf = cmd.make_conf(RS_PORT)
        api_client = rs.ApiClient(conf)
        api_instance = rs.StatusApi(api_client)
        api_response: rs.ApiStatus = api_instance.get_status()
        cmd.display(api_response)

    def _version(self, cmd: StringCommand) -> None:
        self._do_string_command(cmd)


def main() -> None:
    """
    Entry point for the lockssapi command line tool.
    """
    LockssApiCli().run()


if __name__ == '__main__':
    main()
