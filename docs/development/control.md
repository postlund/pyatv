---
layout: template
title: Control
permalink: /development/control/
link_group: development
---
# Control

## Experimental AirPlay receiver relay

AirPlay 2 receivers can relay an existing sender's playback information and
commands. Opt into this experimental mode with `MrpTunnel.Relay`; automatic
selection and the existing AirPlay tunnel are unchanged. Keep the audio sender
playing directly to the receiver. Connecting as a relay does not start audio.

```python
import asyncio
import pyatv
from pyatv.const import Protocol
from pyatv.settings import MrpTunnel
from pyatv.storage.memory_storage import MemoryStorage

async def main():
    loop = asyncio.get_running_loop()
    storage = MemoryStorage()
    devices = await pyatv.scan(loop, protocol=Protocol.AirPlay, storage=storage)
    config = next(device for device in devices if device.name == "Receiver")
    settings = await storage.get_settings(config)
    settings.protocols.airplay.mrp_tunnel = MrpTunnel.Relay
    atv = await pyatv.connect(config, loop, storage=storage)
    try:
        print(await atv.metadata.playing())
        artwork = await atv.metadata.artwork(width=512)
        if artwork:
            print(artwork.mimetype, len(artwork.bytes))
        await atv.remote_control.pause()
        await atv.remote_control.play()
        await atv.remote_control.next()
        await atv.remote_control.previous()
        await atv.remote_control.set_position(90)  # seconds
        await atv.audio.set_volume(50)  # percent, selected receiver
    finally:
        await asyncio.gather(*atv.close())

asyncio.run(main())
```

Each playback call above changes the active sender. Use only the calls you need.
The [relay example](https://github.com/postlund/pyatv/blob/master/examples/airplay_relay.py)
discovers a named receiver and performs one action (default: status):

```shell
python -m examples.airplay_relay "Receiver"
python -m examples.airplay_relay "Receiver" pause
python -m examples.airplay_relay "Receiver" seek 90
python -m examples.airplay_relay "Receiver" volume 50
```

Normal metadata and push updater interfaces report the globally selected
client/player. `metadata.artwork()` reuses the existing artwork retrieval and
cache; it returns `None` when no artwork is available. Requested image dimensions
are a hint, and the sender may return a different size. Playback commands include
that player's complete path and check sender rejection responses. A group shares playback commands; volume targets the
selected receiver's reported output-device UID. To change all reported group
members explicitly, iterate over `atv.audio.output_devices` and pass each member
to `await atv.audio.set_volume(50, member)`. Volume calls wait for a matching
receiver update; a control socket acknowledgment alone does not confirm volume.

This initial implementation supports transient AirPlay pairing and type-130,
controlType-1 streams without a dedicated dataPort. HomeKit authentication,
receiver compatibility beyond the reference, and modifying group membership
remain unverified. Available playback actions depend on the sender's capabilities.
TV navigation and power controls are not provided by this mode.

The transport authenticates its own encrypted AirPlay session, requests an auth
ticket, negotiates the control-only and remote streams, and subscribes over
binary-plist `/command` requests. It uses the event channel for protobuf replies
and updates, sends periodic feedback, and tears down only its own control session.
Existing Media Remote message/state code is reused internally; no standalone MRP
service or audio data socket is opened. No packet interception or sender keys are
required.

Controlling a device is done with the remote control interface,
{% include api i="interface.RemoteControl" %}. It allows you navigate the menus and
change playback (play, pause, etc.).

## Using the Remote Control API

After connecting to a device, you get the remote control via {% include api i="interface.AppleTV.remote_control" %}:

```python
atv = await pyatv.connect(config, ...)
rc = atv.remote_control
```

You can then control via the available functions:

```python
await rc.up()
await rc.select()
await rc.volume_up()
await rc.set_position(100)
```

All available actions can be found in {% include api i="interface.RemoteControl" %}.

## Input Actions

Currently three types of input actions are supported:

* Single tap ("click")
* Double tap ("double click")
* Hold

These actions are supported by the following buttons:

* Arrow keys (up, down, left, right)
* Select
* Menu
* Home

By default, {% include api i="const.InputAction.SingleTap" %} are used. Pass another `action`
to use another input action:

```python
await rc.menu(action=InputAction.Hold)
await rc.home(action=InputAction.DoubleTap)
```

All input actions are specified in {% include api i="const.InputAction" %}.
