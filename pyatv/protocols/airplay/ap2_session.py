"""Implementation of "high-level" support for an AirPlay 2 session.

This code is pretty messy right now and needs some re-structuring. The intention is
however to set up a connection to an AirPlay 2 receiver and ensure encryption and
most low-level stuff is taken care of.
"""

import asyncio
import logging
from random import randint
from typing import Any, Dict, List, Optional, Set, cast
from uuid import uuid4

from pyatv import exceptions
from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import HapCredentials, PairVerifyProcedure
from pyatv.core.protocol import heartbeater
from pyatv.interface import DeviceListener
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import DataStreamChannel, EventChannel
from pyatv.settings import InfoSettings
from pyatv.support.http import HttpConnection, decode_bplist_from_body, http_connect
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


class AP2Session:
    """High-level session for AirPlay 2."""

    def __init__(
        self,
        address: str,
        control_port: int,
        credentials: HapCredentials,
        info: InfoSettings,
    ) -> None:
        """Initialize a new AP2Session instance."""
        self._address = address
        self._control_port = control_port
        self._credentials = credentials
        self._info = info
        self.connection: Optional[HttpConnection] = None
        self.verifier: Optional[PairVerifyProcedure] = None
        self.rtsp: Optional[RtspSession] = None
        self.data_channel: Optional[DataStreamChannel] = None
        self._channels: List[asyncio.BaseTransport] = []
        self._feedback_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Open connection to receiver."""
        _LOGGER.debug(
            "Setting up remote connection to %s:%d",
            self._address,
            self._control_port,
        )

        self.connection = await http_connect(self._address, self._control_port)
        self.verifier = await verify_connection(self._credentials, self.connection)

        self.rtsp = RtspSession(self.connection)

    async def setup_remote_control(self) -> None:
        """Set up remote control session over the data channel."""
        if self.connection is None or self.rtsp is None:
            raise exceptions.InvalidStateError("not connected to remote")

        await self._setup_event_channel(self.connection.remote_ip)
        await self.rtsp.record()
        await self._setup_data_channel(self.connection.remote_ip)

    def start_keep_alive(self, device_listener: StateProducer[DeviceListener]) -> None:
        """Start sending keep alive messages."""

        def _finish_func() -> None:
            device_listener.listener.connection_closed()

        def _failure_func(exc: Exception) -> None:
            device_listener.listener.connection_lost(exc)

        async def _send_feedback(message: Optional[Any]) -> None:
            if self.rtsp:
                await self.rtsp.feedback()

        # Lambdas as needed here as accessing a method in the device listener will
        # cause the device listener to handle that as a connection error happened
        # and tear everything down. This is by design.
        self._feedback_task = asyncio.ensure_future(
            heartbeater(
                name=f"AirPlay:{self._address}",
                sender_func=_send_feedback,
                finish_func=_finish_func,
                failure_func=_failure_func,
                interval=FEEDBACK_INTERVAL,
            )
        )

    async def _setup(self, body: Dict[str, Any]) -> Dict[str, Any]:
        assert self.rtsp
        resp = await self.rtsp.setup(body=body)
        return decode_bplist_from_body(resp)

    async def _setup_event_channel(self, address: str) -> None:
        if self.verifier is None:
            raise exceptions.InvalidStateError("not in connected state")

        resp = await self._setup(
            {
                "isRemoteControlOnly": True,
                "osName": self._info.os_name,
                "sourceVersion": "550.10",
                "timingProtocol": "None",
                "model": self._info.model,
                "deviceID": self._info.device_id,
                "osVersion": self._info.os_version,
                "osBuildVersion": self._info.os_build,
                "macAddress": self._info.mac,
                "sessionUUID": str(uuid4()).upper(),
                "name": self._info.name,
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
        if self.verifier is None:
            raise exceptions.InvalidStateError("not in connected state")

        # A 64 bit random seed is included and used as part of the salt in encryption
        seed = randint(0, 2**64)

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
