---
layout: template
title: Getting Started
permalink: /documentation/getting-started/
link_group: documentation
---
# :raising_hand: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Getting Started

Here is the *jumpstart* guide to get going fast!

# Installation

```shell
pip3 install {{ site.pyatv_version }}
```

See [Installing pyatv](/documentation/#installing-pyatv) for more alternatives.

# Using atvremote

An application called `atvremote` is shipped with pyatv that allows you to
test the library without writing any code. If you just want a simple way to
control a device, this is the way to go.

## Finding a device

Use `scan` to find devices:

```raw
$ atvremote scan
========================================
        Name: Living Room
    Model/SW: 4K tvOS 13.3.1 build 17K795
    Address: 10.0.0.10
        MAC: AA:BB:CC:DD:EE:FF
Identifiers:
    - 01234567-89AB-CDEF-0123-4567890ABCDE
    - 00:11:22:33:44:55
Services:
    - Protocol: MRP, Port: 49152, Credentials: None
    - Protocol: AirPlay, Port: 7000, Credentials: None
```

Each device is identified by one or more unique identifiers. You can pick any
of them and pass to `--id` or use its name with `-n`:

```shell
$ atvremote --id 00:11:22:33:44:54 ...
$ atvremote -n "Living Room" ...
```

This device supports two services: MRP and AirPlay. MRP is used to control the
device. You need to pair with it in order to obtain credentials which are then
used to communicate with it. The same is valid for AirPlay, in case you want to
stream a video to it for instance.

## Pairing process

Pairing with MRP:

```
$ atvremote --id 00:11:22:33:44:54 --protocol mrp pair
Enter PIN on screen: 1234
Pairing seems to have succeeded, yey!
You may now use these credentials: 1650c36b816812561ee1a2ce55441c4d59aeee8287d3d0b90ad41e221c2ccc9b:eb6d47687f82327501d26e77bc3ee8b752034ad397c80cba37d91132717a1721:61383462633431372d383336362d346464632d386533622d333964356265303932663132:39376263616162332d356330652d343136362d623634302d326438656135616161636237
```

The obtained credentials must be passed to `--mrp-credentials` for every call. It
is recommended that you save them to a file, e.g. `mrp_creds`, and call like this:

```raw
atvremote --id 00:11:22:33:44:54 --mrp-credentials `cat mrp_creds` ...
```

If you want to pair any other protocol, you do it in the exact same way but specify
`--protocol xxx` and load the credentials with `--xxx-credentials` where `xxx` is a
protocol name instead.

You can of course specify multiple credentials at once, e.g.
`--mrp-credentials xxx --airplay-credentials yyy`.

```raw
atvremote --id 00:11:22:33:44:54 --mrp-credentials `cat mrp_creds` --airplay-credentials `cat airplay_creds` ...
```

*Note: Currently, pyatv does not have any methods of storing credentials persistently,
that is why this process is cumbersome. Work to improve this is planned for a later
version, see issue {% include issue no="243" %}.*

## Controlling

Once you have credentials, you can start controlling the device and asking for status:

```raw
$ atvremote --id 00:11:22:33:44:54 --mrp-credentials `cat mrp_creds` playing
Media type: Unknown
Play state: Paused
$ atvremote --id ... --mrp-credentials ... play
```

To see all supported commands, pass `commands` as last argument. More detailed instructions
can be found att the [atvremote](../documentation/atvremote/) page.


# Writing code

A simple example that connects to a device and prints what is currently playing looks
like this:

```python
import sys
import asyncio
import pyatv


async def print_what_is_playing(loop):
    """Find a device and print what is playing."""
    print("Discovering devices on network...")
    atvs = await pyatv.scan(loop)

    if not atvs:
        print("No device found", file=sys.stderr)
        return

    config = atvs[0]

    print(f"Connecting to {config.address}")
    atv = await pyatv.connect(config, loop)

    try:
        print(await atv.metadata.playing())
    finally:
        atv.close()  # Do not forget to close


if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(print_what_is_playing(event_loop))
```

You can find this example under `examples/scan_and_connect.py`

# What's next?

It is recommended that you read the [Documentation](../documentation/) section to get
a better grasp of how pyatv works. Then continue with [Development](../development)
once you are ready to write some code. Next is however a tutorial
you can follow if you want to try out creating a simple application!
