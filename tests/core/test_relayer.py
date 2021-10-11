"""Unit tests for pyatv.core.relayer."""
import pytest

from pyatv import exceptions
from pyatv.const import Protocol
from pyatv.core.relayer import Relayer


@pytest.fixture
def relay_base_only():
    relayer = Relayer(BaseClass, [Protocol.MRP])
    relayer.register(SubClass1(), Protocol.MRP)
    yield relayer


class BaseClass:
    def no_args(self):
        pass

    def with_args(self, arg):
        pass

    def with_kwargs(self, **kwargs):
        pass

    @property
    def prop(self):
        pass

    async def async_no_args(self):
        pass

    async def async_with_args(self, arg):
        pass

    async def async_with_kwargs(self, **kwargs):
        pass


class SubClass1(BaseClass):
    def no_args(self):
        return "subclass1"

    def with_args(self, arg):
        return arg * 2

    def with_kwargs(self, **kwargs):
        return kwargs["a"] * kwargs["b"]

    @property
    def prop(self):
        return 123

    async def async_no_args(self):
        return "subclass1"

    async def async_with_args(self, arg):
        return arg * 2

    async def async_with_kwargs(self, **kwargs):
        return kwargs["a"] * kwargs["b"]


class SubClass2(BaseClass):
    def with_args(self, arg):
        return arg


class SubClass3(BaseClass):
    def with_kwargs(self, **kwargs):
        return kwargs["a"] - kwargs["b"]


class SubClass4(BaseClass):
    def __init__(self, ret_string):
        self.ret_string = ret_string

    def no_args(self):
        return self.ret_string


@pytest.mark.asyncio
async def test_base_cases(relay_base_only):
    assert relay_base_only.relay("no_args")() == "subclass1"
    assert relay_base_only.relay("with_args")(3) == 6
    assert relay_base_only.relay("with_kwargs")(a=2, b=3) == 6
    assert relay_base_only.relay("prop") == 123
    assert await relay_base_only.relay("async_no_args")() == "subclass1"
    assert await relay_base_only.relay("async_with_args")(3) == 6
    assert await relay_base_only.relay("async_with_kwargs")(a=2, b=3) == 6


def test_class_priority():
    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay])
    relayer.register(SubClass1(), Protocol.AirPlay)
    relayer.register(SubClass3(), Protocol.MRP)
    relayer.register(SubClass2(), Protocol.DMAP)

    assert relayer.relay("no_args")() == "subclass1"
    assert relayer.relay("with_args")(3) == 3
    assert relayer.relay("with_kwargs")(a=4, b=1) == 3


def test_relay_missing_instance_ignored_and_raises_not_found():
    relayer = Relayer(BaseClass, [Protocol.MRP])

    with pytest.raises(exceptions.NotSupportedError):
        relayer.relay("no_args")


def test_relay_missing_target_raises():
    relayer = Relayer(BaseClass, [Protocol.MRP])
    relayer.register(SubClass2(), Protocol.MRP)

    with pytest.raises(exceptions.NotSupportedError):
        relayer.relay("no_args")


def test_relay_method_not_in_interface_raises():
    relayer = Relayer(BaseClass, [Protocol.MRP])
    relayer.register(SubClass2(), Protocol.MRP)

    with pytest.raises(RuntimeError):
        relayer.relay("missing_method")


def test_add_instance_not_in_priority_list_raises():
    relayer = Relayer(BaseClass, [Protocol.MRP])

    with pytest.raises(RuntimeError):
        relayer.register(SubClass1(), Protocol.DMAP)


def test_relay_override_priority():
    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP])
    relayer.register(SubClass1(), Protocol.DMAP)
    relayer.register(SubClass2(), Protocol.MRP)

    assert relayer.relay("with_args", [Protocol.MRP, Protocol.DMAP])(3) == 3
    assert relayer.relay("with_args", [Protocol.DMAP, Protocol.MRP])(3) == 6


def test_main_instance():
    instance2 = SubClass2()

    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay])
    relayer.register(SubClass1(), Protocol.DMAP)
    relayer.register(SubClass3(), Protocol.AirPlay)
    relayer.register(instance2, Protocol.MRP)

    assert relayer.main_instance == instance2


def test_main_instance_missing_instance_for_priority():
    relayer = Relayer(BaseClass, [Protocol.MRP])
    with pytest.raises(exceptions.NotSupportedError):
        relayer.main_instance


def test_get_instance_of_type():
    instance1 = SubClass1()
    instance2 = SubClass2()
    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay])
    relayer.register(instance1, Protocol.MRP)
    relayer.register(instance2, Protocol.DMAP)

    assert relayer.get(Protocol.MRP) == instance1
    assert relayer.get(Protocol.DMAP) == instance2
    assert relayer.get(Protocol.AirPlay) is None


def test_takeover_and_release():
    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay])
    relayer.register(SubClass4("airplay"), Protocol.AirPlay)
    relayer.register(SubClass4("mrp"), Protocol.MRP)
    relayer.register(SubClass4("dmap"), Protocol.DMAP)

    assert relayer.relay("no_args")() == "mrp"

    relayer.takeover(Protocol.AirPlay)

    assert relayer.relay("no_args")() == "airplay"

    relayer.release()

    assert relayer.relay("no_args")() == "mrp"


def test_takeover_while_takeover_raises():
    relayer = Relayer(BaseClass, [Protocol.AirPlay])
    relayer.register(SubClass4("airplay"), Protocol.AirPlay)
    relayer.takeover(Protocol.DMAP)

    with pytest.raises(exceptions.InvalidStateError):
        relayer.takeover(Protocol.DMAP)


def test_takeover_overrides_manual_priority():
    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay])
    relayer.register(SubClass4("airplay"), Protocol.AirPlay)
    relayer.register(SubClass4("mrp"), Protocol.MRP)
    relayer.register(SubClass4("dmap"), Protocol.DMAP)

    relayer.takeover(Protocol.AirPlay)

    assert (
        relayer.relay("no_args", [Protocol.DMAP, Protocol.MRP, Protocol.AirPlay])()
        == "airplay"
    )


def test_takeover_overrides_main_instance():
    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP])
    relayer.register(SubClass4("mrp"), Protocol.MRP)
    relayer.register(SubClass4("dmap"), Protocol.DMAP)

    relayer.takeover(Protocol.DMAP)

    assert relayer.main_instance.no_args() == "dmap"


def test_get_all_instances():
    mrp = SubClass4("mrp")
    dmap = SubClass4("dmap")
    airplay = SubClass4("airplay")

    relayer = Relayer(BaseClass, [Protocol.MRP, Protocol.DMAP, Protocol.AirPlay])
    relayer.register(mrp, Protocol.MRP)
    relayer.register(dmap, Protocol.DMAP)
    relayer.register(airplay, Protocol.AirPlay)

    instances = relayer.instances
    assert len(instances) == 3
    assert mrp in instances
    assert dmap in instances
    assert airplay in instances
