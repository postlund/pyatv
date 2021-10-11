"""Module containing all protocol logic."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, Generator, Mapping, NamedTuple

from pyatv import interface
from pyatv.const import Protocol
from pyatv.core import MutableService, SetupData, TakeoverMethod
from pyatv.core.scan import ScanMethod
from pyatv.interface import BaseService, DeviceInfo
from pyatv.protocols import airplay as airplay_proto
from pyatv.protocols import companion as companion_proto
from pyatv.protocols import dmap as dmap_proto
from pyatv.protocols import mrp as mrp_proto
from pyatv.protocols import raop as raop_proto
from pyatv.support.http import ClientSessionManager
from pyatv.support.state_producer import StateProducer

SetupMethod = Callable[
    [
        asyncio.AbstractEventLoop,
        interface.BaseConfig,
        interface.BaseService,
        StateProducer,
        ClientSessionManager,
        TakeoverMethod,
    ],
    Generator[SetupData, None, None],
]
PairMethod = Callable[..., interface.PairingHandler]
DeviceInfoMethod = Callable[[str, Mapping[str, Any]], Dict[str, Any]]
ServiceInfoMethod = Callable[
    [MutableService, DeviceInfo, Mapping[Protocol, BaseService]], Awaitable[None]
]


class ProtocolMethods(NamedTuple):
    """Represent implementation of a protocol."""

    setup: SetupMethod
    scan: ScanMethod
    pair: PairMethod
    device_info: DeviceInfoMethod
    service_info: ServiceInfoMethod


PROTOCOLS = {
    Protocol.AirPlay: ProtocolMethods(
        airplay_proto.setup,
        airplay_proto.scan,
        airplay_proto.pair,
        airplay_proto.device_info,
        airplay_proto.service_info,
    ),
    Protocol.Companion: ProtocolMethods(
        companion_proto.setup,
        companion_proto.scan,
        companion_proto.pair,
        companion_proto.device_info,
        companion_proto.service_info,
    ),
    Protocol.DMAP: ProtocolMethods(
        dmap_proto.setup,
        dmap_proto.scan,
        dmap_proto.pair,
        dmap_proto.device_info,
        dmap_proto.service_info,
    ),
    Protocol.MRP: ProtocolMethods(
        mrp_proto.setup,
        mrp_proto.scan,
        mrp_proto.pair,
        mrp_proto.device_info,
        mrp_proto.service_info,
    ),
    Protocol.RAOP: ProtocolMethods(
        raop_proto.setup,
        raop_proto.scan,
        raop_proto.pair,
        raop_proto.device_info,
        raop_proto.service_info,
    ),
}
