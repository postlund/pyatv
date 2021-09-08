"""Module containing all protocol logic."""
import asyncio
from typing import Any, Callable, Dict, Generator, Mapping, NamedTuple

from pyatv import conf, interface
from pyatv.const import Protocol
from pyatv.core import SetupData, StateProducer
from pyatv.core.scan import ScanMethod
from pyatv.protocols import airplay as airplay_proto
from pyatv.protocols import companion as companion_proto
from pyatv.protocols import dmap as dmap_proto
from pyatv.protocols import mrp as mrp_proto
from pyatv.protocols import raop as raop_proto
from pyatv.support.http import ClientSessionManager

SetupMethod = Callable[
    [
        asyncio.AbstractEventLoop,
        conf.AppleTV,
        interface.BaseService,
        StateProducer,
        ClientSessionManager,
    ],
    Generator[SetupData, None, None],
]
PairMethod = Callable[..., interface.PairingHandler]
DeviceInfoMethod = Callable[[Mapping[str, Any]], Dict[str, Any]]


class ProtocolMethods(NamedTuple):
    """Represent implementation of a protocol."""

    setup: SetupMethod
    scan: ScanMethod
    pair: PairMethod
    device_info: DeviceInfoMethod


PROTOCOLS = {
    Protocol.AirPlay: ProtocolMethods(
        airplay_proto.setup,
        airplay_proto.scan,
        airplay_proto.pair,
        airplay_proto.device_info,
    ),
    Protocol.Companion: ProtocolMethods(
        companion_proto.setup,
        companion_proto.scan,
        companion_proto.pair,
        companion_proto.device_info,
    ),
    Protocol.DMAP: ProtocolMethods(
        dmap_proto.setup, dmap_proto.scan, dmap_proto.pair, dmap_proto.device_info
    ),
    Protocol.MRP: ProtocolMethods(
        mrp_proto.setup, mrp_proto.scan, mrp_proto.pair, mrp_proto.device_info
    ),
    Protocol.RAOP: ProtocolMethods(
        raop_proto.setup, raop_proto.scan, raop_proto.pair, raop_proto.device_info
    ),
}
