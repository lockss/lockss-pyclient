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

from pydantic import NonNegativeInt
from pydantic.v1 import BaseModel, Field, NonNegativeInt

from .rs.api_client import ApiClient as RsApiClient
from .rs.api import StatusApi as RsStatusApi, ArtifactsApi as RsArtifactsApi
from .rs import Configuration as RsConfiguration, Artifact
from lockss.pybasic.cliutil import BaseCli, StringCommand, COPYRIGHT_DESCRIPTION, LICENSE_DESCRIPTION, \
    VERSION_DESCRIPTION
from lockss.pybasic.errorutil import InternalError
from . import __copyright__, __license__, __version__

RS_PORT: NonNegativeInt = NonNegativeInt(24610)
RS_DESCRIPTION="LOCKSS Repository Service commands"

class NodeOptions(BaseModel):
    host: str = Field(aliases=["-H"], description="The IP address or FQDN of the LOCKSS node")
    port: Optional[NonNegativeInt] = Field(aliases=["-P"], description="LOCKSS Service API port")

    def make_conf(self, default_port: NonNegativeInt) -> RsConfiguration:
        conf = RsConfiguration()
        conf.host = f'http://{self.host}:{self.port or default_port}'
        return conf

class AuthOptions(NodeOptions):
    username: str = Field(aliases=["-u"], description="LOCKSS API username")
    password: str = Field(aliases=["-p"], description="LOCKSS API password")

    def make_conf(self, default_port: NonNegativeInt) -> RsConfiguration:
        conf = super().make_conf(default_port)
        conf.username = self.username
        conf.password = self.password
        return conf

class AuidOptions(BaseModel):
    namespace: Optional[str] = Field(
        inspect.getfullargspec(Artifact.__init__).defaults[2],
        aliases=["-n"],
        description="LOCKSS namespace")
    auid: str = Field(aliases=["-a"], description="Archival Unit ID")

class RsStatusCommand(NodeOptions):
    pass

class RsGetArtifactsCommand(AuidOptions, AuthOptions):
    pass

class RsArtifactsCommand(BaseModel):
    get_artifacts: Optional[RsGetArtifactsCommand] = Field(
        alias="get-artifacts",
        description="Get a list of all artifacts in a namespace and Archival Unit")

class RsCommand(BaseModel):
    status: Optional[RsStatusCommand] = Field(description="LOCKSS Repository Service API status commands")
    artifacts: Optional[RsArtifactsCommand] = Field(description="LOCKSS Repository Service API artifacts commands")

class LockssApiCommand(BaseModel):
    copyright: Optional[StringCommand.type(__copyright__)] = Field(description=COPYRIGHT_DESCRIPTION)
    license: Optional[StringCommand.type(__license__)] = Field(description=LICENSE_DESCRIPTION)
    version: Optional[StringCommand.type(__version__)] = Field(description=VERSION_DESCRIPTION)
    rs: Optional[RsCommand] = Field(description=RS_DESCRIPTION)

class LockssApiCli(BaseCli[LockssApiCommand]):
    def __init__(self):
        """
        Constructs a new ``DebugPanelCli`` instance.
        """
        super().__init__(model=LockssApiCommand,
                         prog='lockssapi',
                         description='LOCKSS Python client')

    def _do_string_command(self, string_command: StringCommand) -> None:
        """
        Performs one string command.

        :param string_command: A ``StringCommand`` model.
        :type auid_command: StringCommand
        """
        string_command()

    def _copyright(self, string_command: StringCommand) -> None:
        self._do_string_command(string_command)

    def _license(self, string_command: StringCommand) -> None:
        self._do_string_command(string_command)

    def _rs(self, rs_command: RsCommand) -> None:
        raise InternalError()

    def _rs_status(self, status_command: RsStatusCommand) -> None:
        conf = status_command.make_conf(RS_PORT)
        api_client = RsApiClient(conf)
        api_instance = RsStatusApi(api_client)
        api_response = api_instance.get_status()

        print(type(api_response))
        print(api_response.to_str())

    def _rs_artifacts(self, rs_command: RsArtifactsCommand) -> None:
        raise InternalError()

    def _rs_artifacts_get_artifacts(self, rs_get_artifacts_command: RsGetArtifactsCommand) -> None:
        conf = rs_get_artifacts_command.make_conf(RS_PORT)
        print(conf.get_basic_auth_token())
        api_client = RsApiClient(conf, "Authorization", conf.get_basic_auth_token())
        api_instance = RsArtifactsApi(api_client)
        api_response = api_instance.get_artifacts(rs_get_artifacts_command.auid,
                                                  namespace=rs_get_artifacts_command.namespace,
                                                  limit=100)

        print(type(api_response))
        print(api_response.to_str())

    def _version(self, string_command: StringCommand) -> None:
        self._do_string_command(string_command)



def main() -> None:
    """
    Entry point for the lockssapi command line tool.
    """
    LockssApiCli().run()


if __name__ == '__main__':
    main()