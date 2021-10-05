"""Implementation of the Companion protocol."""
from abc import ABC
import asyncio
from enum import Enum
import logging
from typing import Any, Dict, Optional

from pyatv import exceptions
from pyatv.auth.hap_pairing import parse_credentials
from pyatv.auth.hap_srp import SRPAuthHandler
from pyatv.interface import BaseService
from pyatv.protocols.companion import opack
from pyatv.protocols.companion.auth import CompanionPairVerifyProcedure
from pyatv.protocols.companion.connection import (
    CompanionConnection,
    CompanionConnectionListener,
    FrameType,
)
from pyatv.support.collections import SharedData
from pyatv.support.state_producer import StateProducer

_LOGGER = logging.getLogger(__name__)

_OPACK_FRAMES = [
    FrameType.PS_Start,
    FrameType.PS_Next,
    FrameType.PV_Start,
    FrameType.PV_Next,
    FrameType.U_OPACK,
    FrameType.E_OPACK,
    FrameType.P_OPACK,
]

DEFAULT_TIMEOUT = 5.0  # Seconds

SRP_SALT = ""
SRP_OUTPUT_INFO = "ClientEncrypt-main"
SRP_INPUT_INFO = "ServerEncrypt-main"


# pylint: disable=invalid-name


class MessageType(Enum):
    """Type of message."""

    Event = 1
    Request = 2
    Response = 3


# pylint: enable=invalid-name


class CompanionProtocolListener(ABC):
    """Listener interface for Companion protocol."""

    def event_received(self, event_name: str, data: Dict[str, Any]) -> None:
        """Event was received."""


class CompanionProtocol(
    StateProducer[CompanionProtocolListener], CompanionConnectionListener
):
    """Protocol logic related to Companion."""

    def __init__(
        self,
        connection: CompanionConnection,
        srp: SRPAuthHandler,
        service: BaseService,
    ):
        """Initialize a new CompanionProtocol."""
        super().__init__()
        self.connection = connection
        self.connection.listener = self
        self.srp = srp
        self.service = service
        self._queues: Dict[FrameType, asyncio.Queue[SharedData[Any]]] = {}
        self._chacha = None
        self._is_started = False

    def _allocate_shared_data(
        self, frame_type: FrameType, recv_type: FrameType
    ) -> SharedData:
        target_type = recv_type or frame_type
        if target_type not in self._queues:
            self._queues[target_type] = asyncio.Queue()

        shared_data: SharedData[Any] = SharedData()
        self._queues[target_type].put_nowait(shared_data)
        return shared_data

    async def start(self):
        """Connect to device and listen to incoming messages."""
        if self._is_started:
            raise exceptions.ProtocolError("Already started")

        self._is_started = True
        await self.connection.connect()

        if self.service.credentials:
            self.srp.pairing_id = parse_credentials(self.service.credentials).client_id

        _LOGGER.debug("Companion credentials: %s", self.service.credentials)

        await self._setup_encryption()

    def stop(self):
        """Disconnect from device."""
        self.connection.close()

    async def _setup_encryption(self):
        if self.service.credentials:
            credentials = parse_credentials(self.service.credentials)
            pair_verifier = CompanionPairVerifyProcedure(self, self.srp, credentials)

            try:
                await pair_verifier.verify_credentials()
                output_key, input_key = pair_verifier.encryption_keys(
                    SRP_SALT, SRP_OUTPUT_INFO, SRP_INPUT_INFO
                )
                self.connection.enable_encryption(output_key, input_key)
            except Exception as ex:
                raise exceptions.AuthenticationError(str(ex)) from ex

    async def exchange_opack(
        self,
        frame_type: FrameType,
        data: object,
        timeout: float = DEFAULT_TIMEOUT,
        response_type: Optional[FrameType] = None,
    ) -> Dict[str, object]:
        """Send data as OPACK and decode result as OPACK."""
        _LOGGER.debug("Exchange OPACK: %s", data)

        shared_data = self._allocate_shared_data(
            frame_type, response_type or frame_type
        )
        self.send_opack(frame_type, data)
        unpacked_object = await shared_data.wait(timeout)

        if not isinstance(unpacked_object, dict):
            raise exceptions.ProtocolError(
                f"Received unexpected type: {type(unpacked_object)}"
            )

        if "_em" in unpacked_object:
            raise exceptions.ProtocolError(f"Command failed: {unpacked_object['_em']}")

        return unpacked_object

    def send_opack(self, frame_type: FrameType, data: object) -> None:
        """Send data encoded with OPACK."""
        _LOGGER.debug("Send OPACK: %s", data)
        self.connection.send(frame_type, opack.pack(data))

    def frame_received(self, frame_type: FrameType, data: bytes) -> None:
        """Frame was received from remote device."""
        _LOGGER.debug("Received frame %s: %s", frame_type, data)

        if frame_type in _OPACK_FRAMES:
            try:
                # Different handlers can be set up here to deal with other frame
                # formats in the future (if ever needed)
                self._handle_opack(frame_type, data)
            except Exception:
                _LOGGER.exception("failed to process frame")

    def _handle_opack(self, frame_type: FrameType, data: bytes) -> None:
        opack_data, _ = opack.unpack(data)

        _LOGGER.debug("Process incoming OPACK frame (%s): %s", frame_type, opack_data)

        if not isinstance(opack_data, dict):
            _LOGGER.debug("Unsupported OPACK base type: %s", type(opack_data))
            return

        message_type = opack_data.get("_t")
        if message_type == MessageType.Event.value:
            _LOGGER.debug("Received event: %s", opack_data)
            self.listener.event_received(  # pylint: disable=no-member
                opack_data["_i"], opack_data["_c"]
            )
        elif message_type is None or message_type == MessageType.Response.value:
            if not self._queues[frame_type].empty():
                shared_data = self._queues[frame_type].get_nowait()
                shared_data.set(opack_data)
            else:
                _LOGGER.debug("No receiver for frame type %s", frame_type)
        else:
            _LOGGER.warning("Got OPACK frame with unsupported type: %s", message_type)

    def disconnected(self) -> None:
        """Disconnect from companion device."""
