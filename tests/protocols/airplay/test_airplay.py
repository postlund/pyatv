"""Unit tests for pyatv.protocols.airplay."""

from ipaddress import ip_address
from unittest.mock import patch

from deepdiff import DeepDiff
import pytest

from pyatv import exceptions
from pyatv.auth.hap_tlv8 import TlvValue
from pyatv.const import DeviceModel, OperatingSystem, PairingRequirement, Protocol
from pyatv.core import MutableService, create_core, mdns
from pyatv.interface import DeviceInfo
from pyatv.protocols.airplay import device_info, scan, service_info, setup
from pyatv.settings import MrpTunnel

AIRPLAY_SERVICE = "_airplay._tcp.local"


def test_airplay_scan_handlers_present():
    handlers = scan()
    assert len(handlers) == 1
    assert AIRPLAY_SERVICE in handlers


def test_airplay_handler_to_service():
    handler, _ = scan()[AIRPLAY_SERVICE]

    mdns_service = mdns.Service(
        AIRPLAY_SERVICE, "foo", ip_address("127.0.0.1"), 1234, {"foo": "bar"}
    )
    mdns_response = mdns.Response([], False, None)

    name, service = handler(mdns_service, mdns_response)
    assert name == "foo"
    assert service.port == 1234
    assert service.credentials is None
    assert not DeepDiff(service.properties, {"foo": "bar"})


def test_airplay_device_info_name():
    _, device_info_name = scan()[AIRPLAY_SERVICE]
    assert device_info_name("Ohana") == "Ohana"


@pytest.mark.parametrize(
    "service_type,properties,expected",
    [
        ("_dummy._tcp.local", {"model": "unknown"}, {DeviceInfo.RAW_MODEL: "unknown"}),
        (
            "_dummy._tcp.local",
            {"model": "AppleTV6,2"},
            {DeviceInfo.MODEL: DeviceModel.Gen4K, DeviceInfo.RAW_MODEL: "AppleTV6,2"},
        ),
        (
            "_dummy._tcp.local",
            {"model": "MacBookAir10,1"},
            {
                DeviceInfo.RAW_MODEL: "MacBookAir10,1",
                DeviceInfo.OPERATING_SYSTEM: OperatingSystem.MacOS,
            },
        ),
        ("_dummy._tcp.local", {"osvers": "14.7"}, {DeviceInfo.VERSION: "14.7"}),
        (
            "_dummy._tcp.local",
            {"deviceid": "aa:bb:cc:dd:ee:ff"},
            {DeviceInfo.MAC: "aa:bb:cc:dd:ee:ff"},
        ),
        (
            "_dummy._tcp.local",
            {"pi": "AA:BB:CC:DD:EE:FF"},
            {DeviceInfo.OUTPUT_DEVICE_ID: "AA:BB:CC:DD:EE:FF"},
        ),
        (
            "_dummy._tcp.local",
            {"psi": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", "pi": "AA:BB:CC:DD:EE:FF"},
            {DeviceInfo.OUTPUT_DEVICE_ID: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"},
        ),
    ],
)
def test_device_info(service_type, properties, expected):
    assert not DeepDiff(device_info(service_type, properties), expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "airplay_props,mrp_props,requires_password",
    [
        ({}, {}, False),
        ({}, {"pw": "true"}, False),
        ({"pw": "true"}, {}, True),
        ({"pw": "TRUE"}, {}, True),
        ({"sf": "0x80"}, {}, True),
        ({}, {"sf": "0x80"}, False),
        ({"flags": "0x80"}, {}, True),
        ({}, {"flags": "0x80"}, False),
    ],
)
async def test_service_info_password(airplay_props, mrp_props, requires_password):
    airplay_service = MutableService("id", Protocol.AirPlay, 0, airplay_props)
    mrp_service = MutableService("mrp", Protocol.MRP, 0, mrp_props)

    assert not airplay_service.requires_password
    assert not mrp_service.requires_password

    await service_info(
        airplay_service,
        DeviceInfo({}),
        {Protocol.MRP: mrp_service, Protocol.AirPlay: airplay_service},
    )

    assert airplay_service.requires_password == requires_password
    assert not mrp_service.requires_password


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "airplay_props,devinfo,pairing_req",
    [
        ({"sf": "0x0"}, {}, PairingRequirement.NotNeeded),
        ({"sf": "0x8"}, {}, PairingRequirement.Mandatory),
        ({"sf": "0x200"}, {}, PairingRequirement.Mandatory),
        ({"flags": "0x200"}, {}, PairingRequirement.Mandatory),
        ({"acl": "1"}, {}, PairingRequirement.Disabled),
        ({"acl": "1", "sf": "0x200"}, {}, PairingRequirement.Disabled),
        ({"model": "Mac10,1"}, {}, PairingRequirement.Unsupported),
    ],
)
async def test_service_info_pairing(airplay_props, devinfo, pairing_req):
    airplay_service = MutableService("id", Protocol.AirPlay, 0, airplay_props)

    assert airplay_service.pairing == PairingRequirement.Unsupported

    await service_info(
        airplay_service,
        DeviceInfo(devinfo),
        {Protocol.AirPlay: airplay_service},
    )

    assert airplay_service.pairing == pairing_req


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["connect", "setup_remote_control"])
@pytest.mark.parametrize(
    "error,expected",
    [
        (exceptions.AuthenticationError("rejected"), exceptions.AuthenticationError),
        (exceptions.BackOffError("retry later"), exceptions.BackOffError),
        (exceptions.NoCredentialsError("missing"), exceptions.NoCredentialsError),
        (
            exceptions.InvalidCredentialsError("invalid"),
            exceptions.InvalidCredentialsError,
        ),
        (KeyError(TlvValue.Salt), exceptions.ProtocolError),
        (exceptions.InvalidResponseError("invalid response"), exceptions.ProtocolError),
        (
            exceptions.HttpError("credentials required", 470),
            exceptions.InvalidCredentialsError,
        ),
        (exceptions.HttpError("server error", 500), exceptions.HttpError),
    ],
)
async def test_remote_control_connection_errors(
    airplay_conf, session_manager, stage, error, expected
):
    core = await create_core(
        airplay_conf,
        airplay_conf.get_service(Protocol.AirPlay),
        session_manager=session_manager,
    )
    core.settings.protocols.airplay.mrp_tunnel = MrpTunnel.Force

    with patch("pyatv.protocols.airplay.AP2Session", autospec=True) as session_class:
        session = session_class.return_value
        getattr(session, stage).side_effect = error
        session.stop.return_value = set()
        tunnel = next(data for data in setup(core) if data.protocol == Protocol.MRP)

        try:
            with pytest.raises(expected) as raised:
                await tunnel.connect()
            if type(error) is expected:
                assert raised.value is error
            else:
                assert raised.value.__cause__ is error
            session.start_keep_alive.assert_not_called()
        finally:
            tunnel.close()
