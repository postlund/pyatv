---
layout: template
title: Design
permalink: /internals/design
link_group: internals
---
# :construction: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Design

This page gives a brief introduction to the architecture and design of pyatv.

*NB: This page is far from complete and under development. Please let me know if you
want any part of pyatv explained further, so I can add it here.*

# General Topics

This section contains a few topics covering general design concepts, not going into any
protocol specific details.

## Configuration

A *configuration* is a general description of a device and is represented by an instance of
{% include api i="conf.AppleTV" %}. The easiest and best way of obtaining a configuration is
{% include api i="pyatv.scan" %}, as a list of configurations are returned. Both when pairing
and connecting, a configuration is needed.

The configuration instance stores general information about the device, like IP address,
name and various other properties used by the device info interface. It also stores a list
of services associated with the device, i.e. the protocols it supports. A simple overview:

<code class="diagram">
classDiagram
    class AppleTV
    AppleTV : str address
    AppleTV : int port
    AppleTV : ...
    class AirPlayService
    AirPlayService : str identifier
    AirPlayService : int port
    AirPlayService : ...
    class CompanionService
    CompanionService : int port
    CompanionService : ...
    class DmapService
    DmapService : str identifier
    DmapService : int port
    DmapService : ...
    class MrpService
    MrpService : str identifier
    MrpService : int port
    MrpService : ...
    class RaopService
    RaopService : str identifier
    RaopService : int port
    RaopService : ...
    AppleTV --* AirPlayService
    AppleTV --* CompanionService
    AppleTV --* DmapService
    AppleTV --* MrpService
    AppleTV --* RaopService
</code>

## Scanning

Scanning can be performed in one of two ways: unicast or multicast. The different methods are
implemented as separate scanners in {% include code file="support/scan.py" %}:

<code class="diagram">
graph TD
    A[User] -->|hosts=X| B(pyatv.scan)
    B -->|X=None| C[MulticastMdnsScanner]
    B -->|X=10.0.0.2,10.0.0.3| D[UnicastMdnsScanner]
</code>

**UnicastMdnsScanner:** Sends zeroconf requests directly to one or more hosts as specified via the *hosts* argument.

**MulticastMdnsScanner:** Uses multicast and sends requests to all hosts on the network.

Each request contains a list of all the services that pyatv are interested in, i.e. services
used by the implemented protocols. Each protocol must implement a `scan` method returning
which Zeroconf services it needs as well as handlers that are called when a service is found.
An example from Companion looks like this:

```python
def companion_service_handler(
    mdns_service: mdns.Service, response: mdns.Response
) -> ScanHandlerReturn:
    """Parse and return a new Companion service."""
    service = conf.CompanionService(
        mdns_service.port,
        properties=mdns_service.properties,
    )
    return mdns_service.name, service


def scan() -> Mapping[str, ScanHandler]:
    """Return handlers used for scanning."""
    return {"_companion-link._tcp.local": companion_service_handler}
```

Whenever a service with type `_companion-link._tcp.local` is found, the function/handler
`companion_service_handler` is called. Device name and a {% include api i="interface.BaseService" %}
representing the service is returned and added to the final device configuration.

Both unicast (which is a pyatv specific term) and multicast scanning uses a homegrown
implementation of Zeroconf instead of relying on a third party. One exception however
is when publishing new services on the network. In that case
[python-zeroconf](https://github.com/jstasiak/python-zeroconf) is used. Prior to version
0.7.0 of pyatv, python-zerconf would also be used for scanning but some limitations in
the library drove a new implementation. Namely these:

* No other library seems to support sending requests to a specific host, but only allow
  multicast. Unicast was added as an alternative method of scanning for people experiencing
  problems with multicast. It's a very special case but works quite well.
* Not possible to request more than one service at the time in a request. One device in
  pyatv generally depend on service data from more than one service (e.g. MRP and AirPlay).
  Using python-zeroconf, pyatv needed to subscribe to each service independently and await
  all responses. It's not really possible to know when to stop waiting as one cannot know
  how many services to wait for. The implementation in pyatv supports requesting all the
  relevant services at the same time, yielding one response with all service data.
  It means less traffic, more accurate scanning and less waiting.
* Response messages contains a special entry (`_device-info._tcp.local`) which isn't a pure
  service, so it's not possible to subscribe to. It contains the device model, used under
  some circumstances to derive hardware model. Other libraries does not allow access
  to this entry, basically ignoring it, so device info would be lost.

The Zeroconf implementation is in {% include code file="support/mdns.py" %} and some helper
routines for DNS in {% include code file="support/dns.py" %}.

## Connecting

When connecting to a device, an instance of {% include api i="interface.AppleTV" %} is created.
This section describes the basics of how that is done.

### Set up of a protocol instance

When connecting to a device, each service is used to set up a new protocol. This will
create instances of all interface implementations, register them with it's corresponding
relayer (see next section) and connect (if needed by the protocol). Each protocol must
implement a `setup` method and add that to the list in
{% include code file="__init__.py" %} for this to work.

A simple example of a setup method looks like this:

```python
def setup(
    loop: asyncio.AbstractEventLoop,
    config: conf.AppleTV,
    interfaces: Dict[Any, Relayer],
    device_listener: StateProducer,
    session_manager: ClientSessionManager,
) -> Generator[SetupData, None, None]:
    # Service information for current protocol
    service = config.get_service(Protocol.XXX)

    # Create any protocol specific things here
    protocol = DummyProtocol()

    # Register interfaces with corresponding relayers
    interfaces = {
        RemoteControl: DummyRemoteControl(protocol)
    }

    # Called for all protocols _after_ setup has been called for all protocols
    async def _connect() -> bool:
        await protocol.start()
        return True  # Connect succeeded

    # Called when closing the device connection
    def _close() -> Set[asyncio.Task]:
        protocol.stop()
        return set()  # Tasks thas has not yet finished

    # Yield connect handler, close handler and a set with _all_ features supported
    # by the protocol.
    yield SetupData(Protocol.XXX, _connect, _close, interfaces, set([FeatureName.Play]))
```

The `_connect` and `close` methods will be called by the facade object when connecting
or disconnecting. For the feature interface to work properly, each protocol must yield
which features they support. This is used internally in the features implementation in
the facade to know if a protocol implements a certain feature or not.

A protocol can yield as many protocol implementations as they want, even protocols of
a different kind. This is to support the use case where one protocol is tunneled over
another protocol, for instance how MRP is carried over a stream in AirPlay 2.

### Relaying

The general idea of the {% include code file="support/relayer.py" %} module is to allow
protocols to only implement parts of an interface as well as allowing multiple protocols
to implement the same interfaces, but still provide meaningful output to the user. This
is accomplished in two ways:

* There's a built-in priority amongst protocols. If several protocols implement the same
  functionality, the implementation of the protocol with highest priority is picked. The
  general priority is MRP, DMAP, Companion, AirPlay and RAOP.
* The relayer verifies if a protocol has actually provided an implementation of a
  particular member before relaying, ignoring it otherwise.

One relayer is responsible for one interface only. This means that several realyers must
be used to support all the interfaces in pyatv. The facade implementation described below
keeps track of all those relayers.

A typical example of a relayer instance might look like this:

<code class="diagram">
classDiagram
    class Relayer
    Relayer : relay(target, priority)
    class MrpPower
    MrpPower : PowerState power_state
    MrpPower : turn_on(await_new_state)
    MrpPower : turn_off(await_new_state)
    class CompanionPower
    CompanionPower : turn_on(await_new_state)
    CompanionPower : turn_off(await_new_state)
    Relayer --> MrpPower
    Relayer --> CompanionPower
</code>

Here, only `MrpPower` implements {% include api i="interface.Power.power_state" %},
making the relayer always return the value from the MRP implementation. The remaining
methods are implemented by both instances, leaving the choice to priority. A relayer
always has a pre-defined priority list from when it was created (general priority list
mentioned above), but it's also possible to override the internal priority list when
calling the `relay` method. This makes it possible to deal with special cases, where
one protocol with lower priority provides a better implementation than one with
higher priority. The power interface is one such example, where the Companion
implementation is better than MRP (even though MRP has higher general priority than
Companion).

### Facade
The "facade" implements {% include api i="interface.AppleTV" %} as well as all
interfaces belonging to it. One relayer is allocated per interface and protocols
register instances of interfaces they implement during the setup phase (when
connecting). An example with some of the interfaces looks like this:

<code class="diagram">
graph TD
    AppleTV -->|interface.AppleTV| FacadeAppleTV
    FacadeAppleTV -->|interface.Power|PowerRelayer[Relayer]
    FacadeAppleTV -->|interface.Audio|AudioRelayer[Relayer]
    FacadeAppleTV -->|interface.Apps|AppsRelayer[Relayer]
    FacadeAppleTV -->|interface.Remotecontrol|RCRelayer[Relayer]
    PowerRelayer --> CompanionPower
    PowerRelayer --> MrpPower
    AudioRelayer --> RaopAudio
    AppsRelayer --> CompanionApps
    RCRelayer --> DmapRemoteControl
    RCRelayer --> MrpRemoteControl
    RCRelayer --> RaopRemoteControl
</code>

From a user point of view, all interaction occurs with the facade object which
relays calls to the most appropriate protocol instance. A typical interface
implementation looks like this:

```python
class FacadeApps(Relayer, interface.Apps):

    def __init__(self):
        super().__init__(interface.Apps, DEFAULT_PRIORITIES)

    async def app_list(self) -> List[interface.App]:
        return await self.relay("app_list")()

    async def launch_app(self, bundle_id: str) -> None:
        await self.relay("launch_app")(bundle_id)
```

Calls are relayed and potentially returning a value. As described in the relayer
section above, the priority rule is generally used to determine which instance is called.
But the facade can side-step this rule and implement it's own logic when deemed necessary.
One example is the power implementation (short version):

```python
class FacadePower(Relayer, interface.Power, interface.PowerListener):
    OVERRIDE_PRIORITIES = [
        Protocol.Companion,
        Protocol.MRP,
        Protocol.DMAP,
        Protocol.AirPlay,
        Protocol.RAOP,
    ]

    ...

    async def turn_on(self, await_new_state: bool = False) -> None:
        await self.relay("turn_on", priority=self.OVERRIDE_PRIORITIES)(
            await_new_state=await_new_state
        )

```

Here, the priority list is overridden for {% include api i="interface.Power.turn_on" %}
(and {% include api i="interface.Power.turn_off" %}). Another example is the audio
interface:

```python
class FacadeAudio(Relayer, interface.Audio):
    def __init__(self):
        super().__init__(interface.Audio, DEFAULT_PRIORITIES)

    @property
    def volume(self) -> float:
        volume = self.relay("volume")
        if 0.0 <= volume <= 100.0:
            return volume
        raise exceptions.ProtocolError(f"volume {volume} is out of range")

    async def set_volume(self, level: float) -> None:
        if 0.0 <= level <= 100.0:
            await self.relay("set_volume")(level)
        else:
            raise exceptions.ProtocolError(f"volume {level} is out of range")
```

In this case, the facade will guard that an invalid audio level is passed over to the
protocol implementation (i.e. must not be checked there) as well as the value
returned from the protocol.


### General sequence of connecting
Here's a very rough diagram of what happens during a connect call:

<code class="diagram">
sequenceDiagram
    autonumber
    participant User
    participant pyatv
    participant Protocol
    participant Facade
    User ->> pyatv: connect(config)
    loop For each service in config
        pyatv ->> Protocol: setup
        Protocol ->> pyatv: protocol, connect, close, interfaces, feature list
        pyatv ->> Facade: register interfaces
    end
    pyatv ->> Facade: connect
    loop For each protocol
        Facade ->> Protocol: connect
    end
    pyatv ->> User: facade instance
    note over User: Use returned instance
    User ->> Facade: close
    loop For each protocol
        Facade ->> Protocol: close
    end
</code>