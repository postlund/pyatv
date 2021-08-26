"""Implementation of Remote Control (channel) in AirPlay 2."""
import asyncio
import logging
import plistlib
from random import randint
from typing import Any, Dict, List, Optional, cast
from uuid import uuid4

from pyatv.airplay.auth import verify_connection
from pyatv.airplay.channels import DataStreamChannel, EventChannel
from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import HapCredentials, PairVerifyProcedure
from pyatv.interface import BaseService
from pyatv.support.http import HttpConnection, http_connect
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)

# This is what iOS uses
FEEDBACK_INTERVAL = 2.0  # Seconds

EVENTS_SALT = "Events-Salt"
EVENTS_WRITE_INFO = "Events-Write-Encryption-Key"
EVENTS_READ_INFO = "Events-Read-Encryption-Key"

DATASTREAM_SALT = "DataStream-Salt"  # seed must be appended
DATASTREAM_OUTPUT_INFO = "DataStream-Output-Encryption-Key"
DATASTREAM_INPUT_INFO = "DataStream-Input-Encryption-Key"


# TODO: It is not fully understood how to determine if a device supports remote control
# over AirPlay, so this method makes a pure guess. We know that Apple TVs running tvOS
# X (X>=13?) support it as well as HomePods, something we can identify from the model
# string. This implementation should however be improved when it's properly known how
# to check for support.
def is_supported(service: BaseService) -> bool:
    """Return if device supports remote control tunneling."""
    model = service.properties.get("model", "")
    if not model.startswith("AppleTV"):
        return False

    version = service.properties.get("osvers", "0.0")
    return float(version) >= 13.0


class RemoteControl:
    """MRP remote control session over AirPlay."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        address: str,
        control_port: int,
        credentials: HapCredentials,
    ) -> None:
        """Initialize a new RemoteControl instance."""
        self.loop: asyncio.AbstractEventLoop = loop
        self.address: str = address
        self.control_port: int = control_port
        self.connection: Optional[HttpConnection] = None
        self.verifier: Optional[PairVerifyProcedure] = None
        self.rtsp: Optional[RtspSession] = None
        self.credentials: HapCredentials = credentials
        self.data_channel: Optional[DataStreamChannel] = None
        self._channels: List[asyncio.BaseTransport] = []

        self._feedback_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Open remote control connection."""
        _LOGGER.debug(
            "Setting up remote control connection to %s:%d",
            self.address,
            self.control_port,
        )

        self.connection = await http_connect(self.address, self.control_port)
        self.verifier = await verify_connection(self.credentials, self.connection)

        self.rtsp = RtspSession(self.connection)

        resp = await self._setup(
            {
                "isRemoteControlOnly": True,
                "osName": "iPhone OS",
                "sourceVersion": "550.10",
                "timingProtocol": "None",
                "model": "iPhone10,6",
                "deviceID": "FF:EE:DD:CC:BB:AA",
                "osVersion": "14.7.1",
                "osBuildVersion": "18G82",
                "macAddress": "AA:BB:CC:DD:EE:FF",
                "sessionUUID": str(uuid4()).upper(),
                "name": "pyatv",
            }
        )
        await self._setup_event_channel(resp["eventPort"])
        await self.rtsp.record()
        await self._setup_data_channel()

        self._feedback_task = asyncio.ensure_future(self._send_feedback())

    async def _send_feedback(self):
        while True:
            await asyncio.sleep(FEEDBACK_INTERVAL)
            await self.rtsp.feedback()

    async def _setup(self, body: Dict[str, Any]) -> Dict[str, Any]:
        assert self.rtsp

        resp = await self.rtsp.setup(
            headers={"Content-Type": "application/x-apple-binary-plist"},
            body=plistlib.dumps(
                body, fmt=plistlib.FMT_BINARY  # pylint: disable=no-member
            ),
        )
        resp_body = (
            resp.body if isinstance(resp.body, bytes) else resp.body.encode("utf-8")
        )
        return plistlib.loads(resp_body)

    async def _setup_event_channel(self, event_port: int) -> None:
        # Event channel is not used so we don't care about it (must be set up though).
        #
        # Note: Read/Write info reversed here as connection originates from receiver!
        transport, _ = await setup_channel(
            EventChannel,
            self.verifier,
            self.address,
            event_port,
            EVENTS_SALT,
            EVENTS_READ_INFO,
            EVENTS_WRITE_INFO,
        )
        self._channels.append(transport)

    async def _setup_data_channel(self) -> None:
        # A 64 bit random seed is included and used as part of the salt in encryption
        seed = randint(0, 2 ** 64)

        resp = await self._setup(
            {
                "streams": [
                    {
                        "controlType": 2,
                        "channelID": str(uuid4()).upper(),
                        "seed": seed,
                        "clientUUID": str(uuid4()).upper(),
                        "type": 130,
                        "wantsDedicatedSocket": True,
                        "clientTypeUUID": "1910A70F-DBC0-4242-AF95-115DB30604E1",
                    }
                ]
            }
        )

        data_port = resp["streams"][0]["dataPort"]

        transport, protocol = await setup_channel(
            DataStreamChannel,
            self.verifier,
            self.address,
            data_port,
            DATASTREAM_SALT + str(seed),
            DATASTREAM_OUTPUT_INFO,
            DATASTREAM_INPUT_INFO,
        )
        self._channels.append(transport)

        self.data_channel = cast(DataStreamChannel, protocol)

    def stop(self):
        """Close all open connections."""
        if self._feedback_task:
            self._feedback_task.cancel()
        self.connection.close()
        for channel in self._channels:
            channel.close()
