"""Implementation of Remote Control (channel) in AirPlay 2."""
import asyncio
import logging
import plistlib
from random import randint
from typing import Any, Dict, List, Optional, Set, cast
from uuid import uuid4

from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import HapCredentials, PairVerifyProcedure
from pyatv.core.protocol import heartbeater
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import DataStreamChannel, EventChannel
from pyatv.support.http import HttpConnection, http_connect
from pyatv.support.rtsp import RtspSession
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)

# This is what iOS uses
FEEDBACK_INTERVAL = 2.0  # Seconds

EVENTS_SALT = "Events-Salt"
EVENTS_WRITE_INFO = "Events-Write-Encryption-Key"
EVENTS_READ_INFO = "Events-Read-Encryption-Key"

DATASTREAM_SALT = "DataStream-Salt"  # seed must be appended
DATASTREAM_OUTPUT_INFO = "DataStream-Output-Encryption-Key"
DATASTREAM_INPUT_INFO = "DataStream-Input-Encryption-Key"


class RemoteControl:
    """MRP remote control session over AirPlay."""

    def __init__(self, device_listener: StateProducer) -> None:
        """Initialize a new RemoteControl instance."""
        self.connection: Optional[HttpConnection] = None
        self.verifier: Optional[PairVerifyProcedure] = None
        self.rtsp: Optional[RtspSession] = None
        self.device_listener = device_listener
        self.data_channel: Optional[DataStreamChannel] = None
        self._channels: List[asyncio.BaseTransport] = []
        self._feedback_task: Optional[asyncio.Task] = None

    async def start(
        self, address: str, control_port: int, credentials: HapCredentials
    ) -> None:
        """Open remote control connection."""
        _LOGGER.debug(
            "Setting up remote control connection to %s:%d",
            address,
            control_port,
        )

        self.connection = await http_connect(address, control_port)
        self.verifier = await verify_connection(credentials, self.connection)

        self.rtsp = RtspSession(self.connection)

        await self._setup_event_channel(self.connection.remote_ip)
        await self.rtsp.record()
        await self._setup_data_channel(self.connection.remote_ip)

        # Lambdas as needed here as accessing a method in the device listener will
        # cause the device listener to handle that as a connection error happened
        # and tear everything down. This is by design.
        def _finish_func() -> None:
            self.device_listener.listener.connection_closed()

        def _failure_func(exc: Exception) -> None:
            self.device_listener.listener.connection_lost(exc)

        async def _send_feedback(message: Optional[Any]) -> None:
            if self.rtsp:
                await self.rtsp.feedback()

        self._feedback_task = asyncio.ensure_future(
            heartbeater(
                name=f"AirPlay:{address}",
                sender_func=_send_feedback,
                finish_func=_finish_func,
                failure_func=_failure_func,
                interval=FEEDBACK_INTERVAL,
            )
        )

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

    async def _setup_event_channel(self, address: str) -> None:
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

        event_port = resp["eventPort"]

        # Event channel is not used so we don't care about it (must be set up though).
        #
        # Note: Read/Write info reversed here as connection originates from receiver!
        transport, _ = await setup_channel(
            EventChannel,
            self.verifier,
            address,
            event_port,
            EVENTS_SALT,
            EVENTS_READ_INFO,
            EVENTS_WRITE_INFO,
        )
        self._channels.append(transport)

    async def _setup_data_channel(self, address: str) -> None:
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
            address,
            data_port,
            DATASTREAM_SALT + str(seed),
            DATASTREAM_OUTPUT_INFO,
            DATASTREAM_INPUT_INFO,
        )
        self._channels.append(transport)

        self.data_channel = cast(DataStreamChannel, protocol)

    def stop(self) -> Set[asyncio.Task]:
        """Close all open connections."""
        tasks = set()
        if self._feedback_task:
            self._feedback_task.cancel()
            tasks.add(self._feedback_task)
            self._feedback_task = None
        if self.connection:
            self.connection.close()
            self.connection = None
        for channel in self._channels:
            channel.close()
        return tasks
