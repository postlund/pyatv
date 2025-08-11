"""Unit tests for pyatv.storage.

These tests are generally more of the AbstractStorage class but MmoeryStorage is used
since it's a concrete implementation.
"""

from ipaddress import IPv4Address

import pytest

from pyatv import exceptions
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol
from pyatv.storage import StorageModel
from pyatv.storage.memory_storage import MemoryStorage

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="memory_storage")
def memory_storage_fixture() -> MemoryStorage:
    yield MemoryStorage()


async def test_load_save_does_nothing(memory_storage):
    await memory_storage.load()
    await memory_storage.save()


async def test_get_settings_without_identifier_raises(memory_storage):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    with pytest.raises(exceptions.DeviceIdMissingError):
        await memory_storage.get_settings(atv)


@pytest.mark.parametrize(
    "protocol, has_password, setting_name",
    [
        (Protocol.AirPlay, True, "airplay"),
        (Protocol.Companion, False, "companion"),
        (Protocol.DMAP, False, "dmap"),
        (Protocol.MRP, False, "mrp"),
        (Protocol.RAOP, True, "raop"),
    ],
)
async def test_get_settings_for_device(
    memory_storage, protocol, has_password, setting_name
):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(
        ManualService(
            "id",
            protocol,
            1234,
            {},
            credentials="creds",
            password="password" if has_password else None,
        )
    )

    settings = await memory_storage.get_settings(atv)

    assert settings.info.name == "pyatv"
    assert getattr(settings.protocols, setting_name).identifier == "id"
    assert getattr(settings.protocols, setting_name).credentials == "creds"
    if has_password:
        assert getattr(settings.protocols, setting_name).password == "password"


async def test_adding_same_config_returns_existing_settings(memory_storage):
    assert len(memory_storage.settings) == 0

    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id", Protocol.DMAP, 1234, {}))

    await memory_storage.get_settings(atv)
    assert len(memory_storage.settings) == 1

    await memory_storage.get_settings(atv)
    assert len(memory_storage.settings) == 1


async def test_get_all_settings(memory_storage):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id1", Protocol.DMAP, 1234, {}))
    settings = await memory_storage.get_settings(atv)

    atv2 = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv2.add_service(ManualService("id2", Protocol.DMAP, 1234, {}))
    settings2 = await memory_storage.get_settings(atv2)

    assert len(memory_storage.settings) == 2
    assert settings in memory_storage.settings
    assert settings2 in memory_storage.settings


async def test_remove_settings(memory_storage):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id", Protocol.DMAP, 1234, {}))

    settings = await memory_storage.get_settings(atv)
    assert len(memory_storage.settings) == 1

    assert await memory_storage.remove_settings(settings)
    assert len(memory_storage.settings) == 0

    assert not (await memory_storage.remove_settings(settings))


@pytest.mark.parametrize(
    "protocol", [Protocol.AirPlay, Protocol.Companion, Protocol.MRP, Protocol.RAOP]
)
async def test_settings_prioritized_over_config(memory_storage, protocol):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    dmap_service = ManualService("id1", Protocol.DMAP, 1234, {})
    mrp_service = ManualService("id2", protocol, 1234, {}, credentials="creds")
    atv.add_service(dmap_service)
    atv.add_service(mrp_service)

    # Load settings once to insert initial settings into storage
    settings = await memory_storage.get_settings(atv)

    # Change something (credentials in this case) and read from storage again. What is
    # stored in storage should overwrite manual changes.
    dmap_service.credentials = "dmap_creds"
    settings = await memory_storage.get_settings(atv)

    assert settings.protocols.dmap.credentials is None
    assert getattr(settings.protocols, protocol.name.lower()).identifier == "id2"
    assert getattr(settings.protocols, protocol.name.lower()).credentials == "creds"


@pytest.mark.parametrize("protocol", list(Protocol))
async def test_update_config_changes_to_storage(memory_storage, protocol):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    service = ManualService("id2", protocol, 1234, {}, credentials="test")
    atv.add_service(service)

    settings = await memory_storage.get_settings(atv)
    assert getattr(settings.protocols, protocol.name.lower()).credentials == "test"

    # Update credentials with something else and write changes back to storage
    service.credentials = "foobar"
    await memory_storage.update_settings(atv)

    # Verify settings were written to storage
    settings = await memory_storage.get_settings(atv)
    assert getattr(settings.protocols, protocol.name.lower()).credentials == "foobar"


async def test_change_info_is_device_dependent(memory_storage):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id1", Protocol.DMAP, 1234, {}))
    settings = await memory_storage.get_settings(atv)
    settings.info.name = "first"

    atv2 = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv2.add_service(ManualService("id2", Protocol.DMAP, 1234, {}))
    settings2 = await memory_storage.get_settings(atv2)
    settings2.info.name = "second"

    settings = await memory_storage.get_settings(atv)
    assert settings.info.name == "first"


async def test_unsupported_version_raises(memory_storage):
    with pytest.raises(exceptions.SettingsError):
        memory_storage.storage_model = StorageModel(version=2, devices=[])


async def test_change_field_reflected_in_changed_property(memory_storage):
    assert memory_storage.has_changed(dict(memory_storage))
    memory_storage.update_hash(dict(memory_storage))
    assert not memory_storage.has_changed(dict(memory_storage))

    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id1", Protocol.DMAP, 1234, {}))
    settings = await memory_storage.get_settings(atv)

    assert memory_storage.has_changed(dict(memory_storage))
    memory_storage.update_hash(dict(memory_storage))

    settings.info.name = "test"
    assert memory_storage.has_changed(dict(memory_storage))
    memory_storage.update_hash(dict(memory_storage))
    assert not memory_storage.has_changed(dict(memory_storage))


async def test_set_model_reflects_changed_property(memory_storage):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id1", Protocol.DMAP, 1234, {}))
    await memory_storage.get_settings(atv)

    new_storage = MemoryStorage()
    new_storage.update_hash(dict(new_storage))

    new_storage.storage_model = memory_storage.storage_model
    assert new_storage.has_changed(dict(new_storage))

    new_storage.update_hash(dict(new_storage))
    assert not new_storage.has_changed(dict(new_storage))


async def test_save_updates_changed_property(memory_storage):
    atv = AppleTV(IPv4Address("127.0.0.1"), "test")
    atv.add_service(ManualService("id1", Protocol.DMAP, 1234, {}))
    await memory_storage.get_settings(atv)

    assert memory_storage.has_changed(dict(memory_storage))
    await memory_storage.save()
    assert not memory_storage.has_changed(dict(memory_storage))
