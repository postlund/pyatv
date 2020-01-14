---
layout: template
title: Scan, Pair and Connect
permalink: /development/scan_pair_and_connect/
link_group: development
---
# Scan, Pair and Connect

Finding a device, pairing with it and connecting to it are the basic actions needed
to control a device. This page describes how you do this.

## Scanning

### API

```python
async def scan(loop, timeout=5, identifier=None, protocol=None, hosts=None):
```

**loop:** asyncio event loop (e.g. `asyncio.get_event_loop()`)

**timeout:** how long to scan (in seconds) before returning results

**identifier:** filter to scan for *one* particular device

**protocol:** filter fo scan for devices with a particular protocol
(`Protocol.DMAP`, `Protocol.MRP` or `Protocol.AirPlay`)

**hosts:** list of hosts to specifically scan for, e.g. `['10.0.0.1', '10.0.0.2']`

### Usage

Scanning for and printing name and address of all devices can be done like this:

```python
atvs = await pyatv.scan(loop)
for atv in atvs:
    print("Name: {0}, Address: {1}".format(atv.name, atv.address))
```

You can put some limitations on what device(s) to scan for, e.g. an identifier
and/or a protocol:

```python
from pyatv import scan
from pyatv.const import Protocol

# Scan for a specific device
atvs = scan(loop, identifier='AA:BB:CC:DD:EE:FF')

# Scan for a specific device by IP (unicast)
atvs = scan(loop, hosts=['10.0.0.1'])

# Only scan for MRP capable devices
atvs = scan(loop, protocol=Protocol.MRP)
```

A list is always returned, even if a filter is applied.

## Pairing

### API

```python
async def pair(config, protocol, loop, session=None, **kwargs):
```

**config:** configuration for the device of interest

**protocol:** which protocol to pair (service configuration must exist for this protocol)

**loop:** asyncio event loop (e.g. `asyncio.get_event_loop()`)

**session:** optional `aiohtttp.ClientSession` (`pyatv` will create a new if not provided)

**kwargs:** optional arguments to pairing handler (see specific chapter)

### Usage

Calling `pyatv.pair` returns a _pairing handler_ conforming to the interface
`interface.PairingHandler`. The usage flow is more or less generic in order to support
protocols that either requires a PIN entered on the device (`DMAP`) or in the client
(`MRP` and `AirPlay`). It more or less looks like this:

1. Start pairing by calling `begin`
2. Check if device (Apple TV) presents a PIN by checking `device_provides_pin`
  * If True: call `pin` with the PIN shown on screen
  * If False: call `pin` with the PIN that must be
    entered on the device
3. Call `finish`
4. Check if pairing succeeded with `has_paired`
5. Free resources with `close`
6. Obtained resources are available via the service, i.e. `service.credentials`

In a future revision of this API, a function will be added that waits for the pairing
to succeed (or timeout), in order to know when to call `finish`. This is only applicable
to the case when `device_provides_pin` is False. Now you have to poll `has_paired` or
just require that pairing succeeds within a time frame.

If an error occurs, e.g. incorrect PIN, `exceptions.PairingError` is raised.

Translating the flow above into code looks like this:

```python
from pyatv import scan, pair
from pyatv.const import Protocol

atvs = await scan(loop)

pairing = await pair(atvs[0], Protocol.MRP, loop)
await pairing.begin()

pin = int(input("Enter PIN: "))
pairing.pin(pin)
await pairing.finish()

# Give some feedback about the process
if pairing.has_paired:
    print('Paired with device!')
    print('Credentials:', pairing.service.credentials)
else:
    print('Did not pair with device!')

await pairing.close()
```

This is a simplified version of the `examples/pairing.py`.

#### Managing credentials

Credentials are not stored persistently by `pyatv`, that is up to the developer to implement
a solution for that (currently as least). After pairing, make sure to save at least one
identifier and credentials for all services somewhere:

```python
identifier = const.identfier

# Save identifier

for service in config.services:
    protocol = service.protocol
    credentials = service.credentials

    # Save mapping of protocol and credentials
```

Restoring credentials can be done with the following convenience function:

```python
def set_credentials(self, protocol, credentials):
```

And an example:

```python
# Restored from file
identifier = '...'
credentials = {1: 'xxx'}

# Find device and restore credentials
atvs = pyatv.scan(loop, identifier=identifier)

# Error handling here

atv = atvs[0]
for protocol, credentials in credentials.items():
    atv.set_credentials(protocol, credentials)

```

True is returned by `set_credentials` if credentials were set, otherwise
False.

### MRP specifics

This protocol does not support any additional settings.

### DMAP specifics

The following extra settings are supported by `DMAP`:

| Setting | Value |
| ------- | ----- |
| name | Name of the device that is exposed on the network (what you see on your Apple TV). |
| pairing_guid | Custom value for `pairing_guid` (credentials) with format `0xXXXXXXXXXXXXXXXX`. |
| zeroconf | If you want to use a custom `aiozeroconf.Zeroconf` instance, you can pass it here. |

You pass these via `kwargs` to `pyatv.pair`:

```python
pairing = await pyatv.pair(config, Protocol.DMAP, name='my remote')
```

### AirPlay specifics

This protocol does not support any additional settings.

## Connecting

### API

```python
async def connect(config, loop, protocol=None, session=None):
```

**config:** configuration for the device of interest

**loop:** asyncio event loop (e.g. `asyncio.get_event_loop()`)

**protocol:** override which protocol to use (`MRP` is preferred over `DMAP` by default)

**session:** optional `aiohtttp.ClientSession` (`pyatv` will create a new if not provided)

### Usage

Connecting is simply done by passing a config to `pyatv.connect`:

```python
# Get a configuration with scan
atvs = await pyatv.scan(...)

# Connect with obtained configuration
atv = await pyatv.connect(atvs[0], loop)
```

By default, `MRP` will be the preferred protocol if both `MRP` and `DMAP` are present. It
is not possible to connect just `AirPlay` - `exceptions.UnsupportedProtocolError` will be
raised. The configuration must also have an `identifier`, otherwise
`exceptions.DeviceIdMissingError` will be raised.

Remember to load any previously obtained credentials before connecting.

#### Manual configuration

It is possible to bypass the scanning process and manually create a configuration:

```python
config = conf.AppleTV('10.0.0.10', 'Living Room')
config.add_service(conf.DmapService('identifier', '0x123456789ABCDEF0')
atv = await pyatv.connect(config, loop)
```

Please do note that this is not the recommended way as it has a couple of flaws:

* Name and IP-adress might not match the device you expect
* The identifier passed to the service does not make any sense and is not unique anymore
* Dynamic properties, like port numbers, will cause problems (especially for `MRP`)

It can however be convenient to have if you test things when developing `pyatv`
as you can shorten the feedback loop, since scanning can be avoided. But be warned.
