"""Experimental controlType-1 AirPlay relay for existing sender playback."""

import asyncio
from functools import partial
import hashlib
import logging
import math
import platform
from typing import Any, Dict, Optional, Set, Union, cast
from uuid import uuid4

from pyatv import exceptions
from pyatv.auth.hap_channel import setup_channel
from pyatv.auth.hap_pairing import AuthenticationType, HapCredentials
from pyatv.const import FeatureName, Protocol
from pyatv.core import Core, MutableService, SetupData
from pyatv.interface import Metadata, OutputDevice, Power
from pyatv.protocols.airplay.auth import verify_connection
from pyatv.protocols.airplay.channels import BaseDataStreamChannel, BaseEventChannel
from pyatv.protocols.mrp import (
    MrpAudio,
    MrpRemoteControl,
    create_with_connection,
    messages,
    protobuf,
)
from pyatv.protocols.mrp.connection import AbstractMrpConnection
from pyatv.support import async_timeout
from pyatv.support.http import (
    HttpConnection,
    HttpResponse,
    decode_bplist_from_body,
    http_connect,
)
from pyatv.support.rtsp import RtspSession

_LOGGER = logging.getLogger(__name__)


class RelayEvents(BaseEventChannel):
    """Acknowledge receiver requests and enqueue their protobuf messages."""

    def __init__(self, output_key: bytes, input_key: bytes, queue: asyncio.Queue):
        """Initialize an encrypted event channel with a message queue."""
        super().__init__(output_key, input_key)
        self.queue = queue
        self.stream_id: Optional[int] = None

    def handle_received(self) -> None:
        """Parse complete requests, preserving incomplete RTSP data."""
        while self.buffer:
            request, _, rest = self.parse_request(self.buffer)
            if request is None:
                return
            self.buffer = rest
            headers = (
                {"CSeq": request.headers["CSeq"]} if "CSeq" in request.headers else {}
            )
            self.send(
                self.format_response(
                    HttpResponse(
                        request.protocol, request.version, 200, "OK", headers, b""
                    )
                )
            )
            if (request.method, request.path) != ("POST", "/command"):
                continue
            if request.headers.get("X-Apple-StreamID") not in (
                None,
                str(self.stream_id),
            ):
                continue
            payload = BaseDataStreamChannel.decode_payload(cast(bytes, request.body))
            raw = (
                payload.get("params", {}).get("data")
                if isinstance(payload, dict)
                else None
            )
            if isinstance(raw, bytes):
                for message in BaseDataStreamChannel.decode_protobufs(raw):
                    self.queue.put_nowait(message)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Wake the consumer when the encrypted event connection ends."""
        self.queue.put_nowait(exc or EOFError("AirPlay event connection closed"))


class RelayConnection(AbstractMrpConnection):
    """Carry protobuf messages over encrypted AirPlay control and event channels."""

    def __init__(self, core: Core, credentials: HapCredentials) -> None:
        """Initialize an independent controller for the advertised receiver."""
        super().__init__()
        self.core = core
        self.credentials = credentials
        self.identifier = str(uuid4()).upper()
        mac = bytearray(hashlib.sha256(self.identifier.encode()).digest()[:6])
        mac[0] = (mac[0] | 2) & 254
        self.mac = ":".join(f"{part:02X}" for part in mac)
        self.connection: Optional[HttpConnection] = None
        self.rtsp: Optional[RtspSession] = None
        self.control_setup = False
        self.events: Optional[RelayEvents] = None
        self.stream_id: Optional[int] = None
        self.tasks: Set[asyncio.Task] = set()
        self.queue: asyncio.Queue[Union[protobuf.ProtocolMessage, Exception]] = (
            asyncio.Queue()
        )
        self.outgoing: asyncio.Queue[protobuf.ProtocolMessage] = asyncio.Queue()
        self.paths: Dict[tuple, protobuf.PlayerPath] = {}
        self.lock = asyncio.Lock()
        self.closing = False
        self.close_task: Optional[asyncio.Task] = None

    @property
    def connected(self) -> bool:
        """Return whether both owned channels are ready."""
        return self.stream_id is not None and not self.closing

    def enable_encryption(self, output_key: bytes, input_key: bytes) -> None:
        """Reject a second authentication layer inside the encrypted relay."""
        raise exceptions.NotSupportedError("Relay encryption is negotiated by AirPlay")

    async def exchange(
        self, method: str, path: Optional[str] = None, **kwargs: Any
    ) -> HttpResponse:
        """Serialize control requests, including feedback and commands."""
        assert self.rtsp
        headers = {
            "User-Agent": "AirPlay/980.77.1",
            "X-Apple-ProtocolVersion": "1",
            **kwargs.pop("headers", {}),
        }
        async with self.lock, async_timeout(8):
            return await self.rtsp.exchange(method, path, headers=headers, **kwargs)

    async def connect(self) -> None:
        """Authenticate and subscribe without requesting an audio stream."""
        self.connection = await http_connect(
            str(self.core.config.address), self.core.service.port
        )
        self.rtsp = RtspSession(self.connection)
        await self.exchange("GET", "/info", body={"qualifier": ["txtAirPlay"]})
        verifier = await verify_connection(self.credentials, self.connection)
        await self.exchange(
            "POST",
            "/auth-setup",
            headers={"X-Apple-AT": "16"},
            body={"ascm": 1, "tkrd": ["pair", "auth", "uuid"]},
        )
        response = await self.exchange(
            "SETUP",
            body={
                "isRemoteControlOnly": True,
                "timingProtocol": "None",
                "statsCollectionEnabled": False,
                "updateSessionRequest": False,
                "combinedGetInfoWithControlSetup": True,
                "sessionUUID": str(uuid4()).upper(),
                "sessionCorrelationUUID": self.identifier,
                "deviceID": self.mac,
                "macAddress": self.mac,
                "name": "pyatv relay",
                "model": "pyatv",
                "osName": platform.system(),
                "osVersion": platform.release(),
                "sourceVersion": "980.77.1",
            },
        )
        self.control_setup = True
        event_port = decode_bplist_from_body(response)["eventPort"]
        if (
            not isinstance(event_port, int)
            or isinstance(event_port, bool)
            or not 1 <= event_port <= 65535
        ):
            raise exceptions.InvalidResponseError("Invalid eventPort")
        await self.exchange("GET", "/info")
        _, channel = await setup_channel(
            lambda output, incoming: RelayEvents(output, incoming, self.queue),
            verifier,
            self.connection.remote_ip,
            event_port,
            "Events-Salt",
            "Events-Read-Encryption-Key",
            "Events-Write-Encryption-Key",
        )
        self.events = cast(RelayEvents, channel)
        self._background(self.consume())
        await self.exchange("RECORD")
        response = await self.exchange(
            "SETUP",
            body={
                "streams": [
                    {
                        "type": 130,
                        "controlType": 1,
                        "clientUUID": str(uuid4()).upper(),
                        "channelID": str(uuid4()).upper(),
                        "clientTypeUUID": "1910A70F-DBC0-4242-AF95-115DB30604E1",
                    }
                ]
            },
        )
        streams = decode_bplist_from_body(response).get("streams", [])
        if (
            len(streams) != 1
            or streams[0].get("type") != 130
            or "dataPort" in streams[0]
        ):
            raise exceptions.InvalidResponseError(
                "Expected a two-channel remote stream"
            )
        stream_id = streams[0].get("streamID")
        if (
            not isinstance(stream_id, int)
            or isinstance(stream_id, bool)
            or not 0 <= stream_id < 2**32
        ):
            raise exceptions.InvalidResponseError("Invalid remote streamID")
        self.stream_id = self.events.stream_id = stream_id
        self._background(self._send_messages())
        self._background(self.feedback())

    def _background(self, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self._completed)

    def _completed(self, task: asyncio.Task) -> None:
        if task.cancelled() or self.closing:
            return
        error = task.exception()
        if error:
            _LOGGER.error("AirPlay relay connection failed: %s", error)
            self.listener.stop()
            self.core.device_listener.listener.connection_lost(error)

    def send(self, message: protobuf.ProtocolMessage) -> None:
        """Queue a message, adjusting only the native relay subscription."""
        if not self.connected:
            raise exceptions.InvalidStateError("Relay is not connected")
        native = protobuf.ProtocolMessage()
        native.CopyFrom(message)
        if native.type == protobuf.DEVICE_INFO_MESSAGE:
            inner = protobuf.extract_inner(native)
            inner.Clear()
            for field, value in {
                "uniqueIdentifier": self.identifier,
                "name": self.core.settings.info.name,
                "localizedModelName": "Mac",
                "applicationBundleIdentifier": "local.pyatv.relay",
                "protocolVersion": 1,
                "lastSupportedMessageType": 65,
                "allowsPairing": False,
                "supportsSharedQueue": True,
                "sharedQueueVersion": 3,
                "deviceUID": self.mac,
                "deviceClass": protobuf.DeviceClass.Mac,
                "logicalDeviceCount": 1,
                "isProxyGroupPlayer": False,
                "isAirplayActive": False,
                "modelID": "pyatv",
            }.items():
                setattr(inner, field, value)
        elif native.type == protobuf.CLIENT_UPDATES_CONFIG_MESSAGE:
            protobuf.extract_inner(native).CopyFrom(
                protobuf.extract_inner(messages.client_updates_config(keyboard=False))
            )
            # Unnamed field 6 must be false for this native subscription.
            native.MergeFromString(b"\xaa\x01\x02\x30\x00")
        self.outgoing.put_nowait(native)

    async def _send_messages(self) -> None:
        while True:
            message = await self.outgoing.get()
            await self.exchange(
                "POST",
                "/command",
                headers={"X-Apple-StreamID": str(self.stream_id)},
                body={
                    "params": {
                        "data": BaseDataStreamChannel.encode_protobufs([message])
                    }
                },
            )

    async def consume(self) -> None:
        """Deliver replies and cache full player paths without selecting a player."""
        while True:
            message = await self.queue.get()
            if isinstance(message, Exception):
                raise message
            if message.type == protobuf.SET_STATE_MESSAGE:
                path = protobuf.extract_inner(message).playerPath
                copy = protobuf.PlayerPath()
                copy.CopyFrom(path)
                self.paths[path.client.bundleIdentifier, path.player.identifier] = copy
            self.listener.message_received(message, message.SerializeToString())

    async def feedback(self) -> None:
        """Keep the control-only session alive with two-second feedback."""
        while True:
            await self.exchange("POST", "/feedback")
            await asyncio.sleep(2)

    def close(self) -> None:
        """Schedule teardown and expose its task to the owning facade."""
        if not self.closing:
            self.closing = True
            self.close_task = asyncio.create_task(self._close())

    async def _close(self) -> None:
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        try:
            if self.rtsp and self.control_setup:
                await asyncio.wait_for(self.exchange("TEARDOWN", body={}), 2)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug("Relay teardown failed", exc_info=True)
        finally:
            if self.events:
                self.events.close()
            if self.connection:
                self.connection.close()


class RelayRemoteControl(MrpRemoteControl):
    """Address playback commands to the globally selected sender player."""

    def __init__(self, loop, psm, protocol) -> None:
        """Reuse normal player selection and the native connection's full paths."""
        super().__init__(loop, psm, protocol)
        self.connection = cast(RelayConnection, protocol.connection)

    async def _send_command(self, command, **kwargs):
        if not self.psm.client:
            raise exceptions.InvalidStateError("No active sender")
        path = self.connection.paths.get(
            (self.psm.client.bundle_identifier, self.psm.playing.identifier)
        )
        if path is None:
            raise exceptions.InvalidStateError("No active player path")
        message = messages.command(command, **kwargs)
        protobuf.extract_inner(message).playerPath.CopyFrom(path)
        response = await self.protocol.send_and_receive(message)
        if response.errorCode or response.type != protobuf.SEND_COMMAND_RESULT_MESSAGE:
            raise exceptions.CommandError("Invalid or rejected relay command response")
        result = protobuf.extract_inner(response)
        if (
            result.sendError
            or result.handlerReturnStatus
            or result.commandResult.sendError
            or any(status.statusCode for status in result.commandResult.statuses)
        ):
            raise exceptions.CommandError("Relay command rejected by sender")

    async def set_position(self, pos: int) -> None:
        """Seek the selected sender to a finite, nonnegative position in seconds."""
        if not math.isfinite(pos) or pos < 0:
            raise exceptions.CommandError("Position must be finite and nonnegative")
        await self._send_command(
            protobuf.CommandInfo_pb2.SeekToPlaybackPosition,
            playbackPosition=pos,
            sendOptions=0,
        )


class RelayAudio(MrpAudio):
    """Control a receiver's volume using its reported group-member UID."""

    def __init__(self, protocol, state_dispatcher, receiver_id: str) -> None:
        """Bind volume to the receiver, independently of the source device."""
        self.receiver_id = receiver_id.replace(":", "").lower()
        self.levels: Dict[str, float] = {}
        self.changed = asyncio.Event()
        super().__init__(protocol, state_dispatcher)

    @property
    def device_uid(self) -> Optional[str]:
        """Find the requested receiver among the sender's reported output devices."""
        for device in self.output_devices:
            if device.identifier.replace(":", "").lower() == self.receiver_id:
                return device.identifier
        return None

    async def _volume_did_change(self, message) -> None:
        inner = protobuf.extract_inner(message)
        uid = inner.outputDeviceUID or inner.endpointUID
        if not math.isfinite(inner.volume) or not 0 <= inner.volume <= 1:
            return
        self.levels[uid] = inner.volume * 100
        if uid == self.device_uid:
            self._volume_controls_available = True
            self._volume_controls_absolute = True
        inner.outputDeviceUID = uid
        await super()._volume_did_change(message)
        self.changed.set()

    async def set_volume(
        self, level: float, output_device: Optional[OutputDevice] = None
    ) -> None:
        """Set absolute volume and wait for a matching receiver update."""
        if not math.isfinite(level) or not 0 <= level <= 100:
            raise exceptions.CommandError("Volume must be between 0 and 100")
        uid = output_device.identifier if output_device else self.device_uid
        if uid is None or uid not in {
            device.identifier for device in self.output_devices
        }:
            raise exceptions.InvalidStateError(
                "Receiver not found in reported output devices"
            )
        self.changed.clear()
        response = await self.protocol.send_and_receive(
            messages.set_volume(uid, level / 100)
        )
        if response.errorCode:
            raise exceptions.CommandError("Relay volume command rejected")
        async with async_timeout(5):
            while abs(self.levels.get(uid, -1) - level) > 0.5:
                self.changed.clear()
                await self.changed.wait()


def setup(core: Core, credentials: HapCredentials) -> SetupData:
    """Expose a native AirPlay relay through the existing pyatv interfaces."""
    if credentials.type != AuthenticationType.Transient:
        raise exceptions.NotSupportedError(
            "Experimental relay requires transient AirPlay pairing"
        )
    connection = RelayConnection(core, credentials)
    service = MutableService(None, Protocol.MRP, core.service.port, {})
    mrp_core = Core(
        core.loop,
        core.config,
        service,
        core.settings,
        core.device_listener,
        core.session_manager,
        core.takeover,
        core.state_dispatcher.create_copy(Protocol.MRP),
    )
    data = create_with_connection(
        mrp_core,
        connection,
        requires_heatbeat=False,
        skip_keyboard=True,
        remote_control_factory=RelayRemoteControl,
        audio_factory=partial(
            RelayAudio, receiver_id=core.service.properties.get("deviceid", "")
        ),
    )
    interfaces = dict(data.interfaces)
    interfaces.pop(Power)
    # Native receiver playback control does not provide a TV navigation interface.
    supported = {
        FeatureName.Artwork,
        FeatureName.Play,
        FeatureName.Pause,
        FeatureName.PlayPause,
        FeatureName.Next,
        FeatureName.Previous,
        FeatureName.SetPosition,
        FeatureName.Title,
        FeatureName.Artist,
        FeatureName.Album,
        FeatureName.Genre,
        FeatureName.TotalTime,
        FeatureName.Position,
        FeatureName.Volume,
        FeatureName.SetVolume,
        FeatureName.VolumeUp,
        FeatureName.VolumeDown,
        FeatureName.App,
        FeatureName.OutputDevices,
    }

    async def connect() -> bool:
        result = await data.connect()
        metadata = cast(Metadata, interfaces[Metadata])
        # Initial player events can follow the subscription acknowledgment.
        for _ in range(20):
            if (await metadata.playing()).title:
                break
            await asyncio.sleep(0.1)
        return result

    def close() -> Set[asyncio.Task]:
        tasks = data.close()
        if connection.close_task:
            tasks.add(connection.close_task)
        return tasks

    return SetupData(Protocol.MRP, connect, close, lambda: {}, interfaces, supported)
