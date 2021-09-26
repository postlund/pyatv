---
layout: template
title: Scan, Pair and Connect
permalink: /development/scan_pair_and_connect/
link_group: development
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# Scan, Pair and Connect

Finding a device, pairing with it and connecting to it are the basic actions needed
to control a device.

# Scan

Use {% include api i="pyatv.scan" %} to scan for devices on the local network.
Scanning for and printing name and address of discovered devices can be done like this:

```python
atvs = await pyatv.scan(loop)
for atv in atvs:
    print(f"Name: {atv.name}, Address: {atv.address}")
```

You can put some limitations on what device(s) to scan for, e.g. an identifier
and/or a protocol:

```python
from pyatv import scan
from pyatv.const import Protocol

# Scan for a specific device
atvs = scan(loop, identifier="AA:BB:CC:DD:EE:FF")

# Scan for a specific device by IP (unicast)
atvs = scan(loop, hosts=["10.0.0.1"])

# Only scan for MRP services
atvs = scan(loop, protocol=Protocol.MRP)

# Include both MRP and AirPlay
atvs = scan(loop, protocol={Protocol.MRP, Protocol.AirPlay})
```

A list is always returned, even if a filter is applied. See
{% include api i="conf.AppleTV" %} for what you can do with a configuration
(e.g. extract deep sleep state or available services).

When scanning for one or more protocols with `protocols`, only the listed
protocols are added to the configuration regardless if more protocols are
supported.

It is possible to provide a `set` of identifiers to scan for:

```python
atvs = scan(loop, identifier={"id1", "id2"})
```

The first device responding to either of the identifiers will be returned.
This is useful when re-discovering a previous known device. Scanning for
all identifiers used by a device will work even if a service is no longer
present, e.g. when disabling AirPlay.

# Pair

Calling {% include api i="pyatv.pair" %} returns a _pairing handler_ conforming to the interface
{% include api i="interface.PairingHandler" %}. The usage flow is generic in order to support
protocols that either require a PIN entered on the device (`DMAP`) or in the client
(`MRP` and `AirPlay`).

## Pairing Requirement

Not all protocols support nor require pairing, it is thus necessary to verify if pairing is
needed before calling {% include api i="pyatv.pair" %}. After performing a scan, the
{% include api i="interface.BaseService.pairing" %} property return whether pairing is required
or not. There are five states to consider:

| Requirement | Meaning |
| ----------- | ------- |
| {% include api i="const.PairingRequirement.Unsupported" %} | Pairing is either not supported by protocol or not implemented by pyatv.
| {% include api i="const.PairingRequirement.Disabled" %} | Pairing is generally supported by the protocol, but has been (temporarily) disabled by the device.
| {% include api i="const.PairingRequirement.NotNeeded" %} | Pairing is not needed, i.e. it is possible to connect without any further action.
| {% include api i="const.PairingRequirement.Optional" %} | Pairing is not needed but recommended. One example is when Home Sharing is enabled, where credentials are included in the Zeroconf properties.
| {% include api i="const.PairingRequirement.Mandatory" %} | Pairing must be performed.

The pairing requirement is solely based on what is required by a protocol and does not take
any provided credentials into account, i.e. {% include api i="interface.BaseService.pairing" %}
will return {% include api i="const.PairingRequirement.Mandatory" %} even when credentials
are filled in.

{% include api i="pyatv.pair" %} must only be called if {% include api i="interface.BaseService.pairing" %}
is either {% include api i="const.PairingRequirement.Optional" %} or
{% include api i="const.PairingRequirement.Mandatory" %}.

## Pairing Flow

The general flow for pairing looks like this.

1. Start pairing by calling `begin`
2. Check if device presents a PIN by checking `device_provides_pin`
  * If True: call `pin` with the PIN shown on screen
  * If False: call `pin` with the PIN that must be
    entered on the device and wait for user to enter PIN
3. Call `finish`
4. Check if pairing succeeded with `has_paired`
5. Free resources with `close`
6. Obtained credentials are available via the service, i.e. `service.credentials`

In a future revision of this API, a function will be added that waits for the pairing
to succeed (or timeout), in order to know when to call `finish`. This is only applicable
to the case when `device_provides_pin` is False. Now you have to poll `has_paired` or
just require that pairing succeeds within a time frame.

If an error occurs, e.g. incorrect PIN, {% include api i="exceptions.PairingError" %} is raised.

Translating the flow above into code looks like this (this is a simplified version of `examples/pairing.py`):

```python
import asyncio
from pyatv import scan, pair
from pyatv.const import Protocol

async def main():
    loop = asyncio.get_event_loop()

    atvs = await scan(loop)

    pairing = await pair(atvs[0], Protocol.MRP, loop)
    await pairing.begin()

    if pairing.device_provides_pin:
        pin = int(input("Enter PIN: "))
        pairing.pin(pin)
    else:
        pairing.pin(1234)  # Should be randomized
        input("Enter this PIN on the device: 1234")

    await pairing.finish()

    # Give some feedback about the process
    if pairing.has_paired:
        print("Paired with device!")
        print("Credentials:", pairing.service.credentials)
    else:
        print("Did not pair with device!")

    await pairing.close()

asyncio.run(main())  # asyncio.run requires python 3.7+
```

## Storing credentials

Credentials are not stored persistently by pyatv. It is up to the developer to implement
a solution for that. After pairing, make sure to save at least one
identifier and credentials for all services somewhere:

```python
identifier = const.identfier

# Save identifier

for service in config.services:
    protocol = service.protocol
    credentials = service.credentials

    # Save mapping of protocol and credentials
```

How to restore credentials is described in [here](#restoring-credentials).

## Protocol specific settings

Some protocols support protocol specific setting, e.g. a special name or identifier.
This section covers protocol specific settings, which at this time is only supported by `DMAP`.

### DMAP specifics

The following extra settings are supported by `DMAP`:

| Setting | Value |
| ------- | ----- |
| name | Name of the device that is exposed on the network (what you see on your Apple TV). |
| pairing_guid | Custom value for `pairing_guid` (credentials) with format `0xXXXXXXXXXXXXXXXX`. |
| zeroconf | If you want to use a custom `zeroconf.Zeroconf` instance, you can pass it here. |

You pass these via `kwargs` to {% include api i="pyatv.pair" %}:

```python
pairing = await pyatv.pair(config, Protocol.DMAP, name="my remote")
```

# Connect

Connecting is simply done by passing a config to {% include api i="pyatv.conncet" %}:

```python
# Get a configuration with scan
atvs = await pyatv.scan(...)

# Apple TV configuration (first found device in this case)
conf = atvs[0]

# Connect with obtained configuration
atv = await pyatv.connect(atvs[0], loop)
```

If the configuration contains no services (only possible when manually
creating a config), a {% include api i="exceptions.NoServiceError" %} will
be raised. The configuration must have an `identifier`, otherwise
{% include api i="exceptions.DeviceIdMissingError" %}  will be raised.

If you have previously stored any credentials, you can need to load them again before
connecting, see next chapter.

*Note: Prior to version 0.8.0, the protocol argument specified which "main"
protocol to use. This is no longer needed as the most appropriate protocol
will be used automatically.*

## Restoring credentials

Restoring credentials is performed with {% include api i="conf.AppleTV.set_credentials" %}:

```python
# Restored from file
identifier = "..."
stored_credentials = {Protocol.MRP: "xxx"}

# Find device and restore credentials
atvs = pyatv.scan(loop, identifier=identifier)

# Error handling here

atv = atvs[0]
for protocol, credentials in stored_credentials.items():
    atv.set_credentials(protocol, credentials)
```

True is returned if credentials were set, otherwise False.

## Manual configuration

It is possible to bypass the scanning process and manually create a configuration:

```python
service = conf.ManualService(
    "identifier", Protocol.DMAP, 3689, {}, credentials="0x123456789ABCDEF0"
)
config = conf.AppleTV("10.0.0.10", "Living Room")
config.add_service(service)
atv = await pyatv.connect(config, loop)
```

Please do note that this is not the recommended way as it has a couple of flaws:

* Name and IP-adress might not match the device you expect
* The identifier passed to the service does not make any sense and is not unique anymore
* Dynamic properties, like port numbers, will cause problems

It can however be convenient to have if you test things when developing pyatv
as you can shorten the feedback loop, since scanning can be avoided. But be warned.

*NB: Service specific services, e.g. {% include api i="conf.DmapService" %} is deprecated
as of 0.9.0. Please use {% include api i="conf.ManualService" %} instead.*

## Closing connection

To close the connection, use {% include api i="interface.AppleTV.close" %}:

```python
atv = await pyatv.connect(config, loop)

# Do something

atv.close()
```

A set of pending tasks are returned by {% include api i="interface.AppleTV.close" %},
which can be awaited to make sure everything has been torn down:

```python
await asyncio.gather(*atv.close())
```