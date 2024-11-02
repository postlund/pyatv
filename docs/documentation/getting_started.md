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

To set up a device, you either use the "wizard" that will guide
you through setting up a new device _or_ manually perform all steps. The wizard
is still in beta stage, but still recommended as it is easier to use.

## Method 1: Wizard (recommended)

Just run `atvremote wizard`, pick a device from the list and follow the steps:

```raw
$ atvremote wizard
Looking for devices...
Found the following devices:
    Name                      Model                    Address
--  ------------------------  -----------------------  -----------
 1  Vardagsrum                Apple TV 4K              10.0.10.81
 2  Receiver                  RX-V773                  10.0.10.82
 3  Pierre's AirPort Express  AirPort Express (gen 2)  10.0.10.168
 4  Apple TV                  Apple TV 3               10.0.10.83
 5  Office                    HomePod Mini             10.0.10.84
Enter index of device to set up (q to quit): 5
Starting to set up Office
Ignoring AirPlay since pairing is not needed
Ignoring RAOP since pairing is not needed
Pairing finished, trying to connect and get some metadata...
Currently playing:
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off
Device is now set up!
```

You might have to enter PIN codes a few times. As long as you get
`Device is now set up!`, you are ready to go and can move on to
[Controlling](#controlling).

## Method 2: Manual

### Finding a device

Use `scan` to find devices:

```raw
$ atvremote scan
========================================
       Name: Vardagsrum
   Model/SW: Apple TV 4K, tvOS 16.6 build 20M73
    Address: 10.0.10.81
        MAC: 00:11:22:33:44:55
 Deep Sleep: True
Identifiers:
 - 01234567-89AB-CDEF-0123-4567890ABCDE
 - 00:11:22:33:44:55
 - 11223344-5566-7788-9900-112233445566
 - 001122334455

Services:
 - Protocol: Companion, Port: 49153, Credentials: None, Requires Password: False, Password: None, Pairing: Mandatory
 - Protocol: AirPlay, Port: 7000, Credentials: None, Requires Password: False, Password: None, Pairing: Mandatory
 - Protocol: MRP, Port: 49154, Credentials: None, Requires Password: False, Password: None, Pairing: NotNeeded (Disabled)
 - Protocol: RAOP, Port: 7000, Credentials: None, Requires Password: False, Password: None, Pairing: Mandatory
```

Each device is identified by one or more unique identifiers. You can pick any
of them and pass to `--id` or use its name with `-n`:

```shell
$ atvremote --id 00:11:22:33:44:55 ...
$ atvremote -n "Living Room" ...
```

This device supports four services: Companion, AirPlay MRP and RAOP. Each service (or protocol)
provides a certain set of features, e.g. AirPlay might provide metadata and playback controls,
Companion allows app launching and RAOP audio streaming. In reality, you should not care about
that. Just make sure you pair all protocols and let `pyatv` figure out what each protocol supports,
that will provide you with as much functionality as possible.

The pairing process is described in the next section. Please note that MRP is marked as *Disabled*
(at the end of the line), meaning it can *not* be paired (simply ignore it).

### Pairing process

Pairing with AirPlay:

```
$ atvremote --id 00:11:22:33:44:54 --protocol airplay pair
Enter PIN on screen: 1234
Pairing seems to have succeeded, yey!
You may now use these credentials: 1650c36b816812561ee1a2ce55441c4d59aeee8287d3d0b90ad41e221c2ccc9b:eb6d47687f82327501d26e77bc3ee8b752034ad397c80cba37d91132717a1721:61383462633431372d383336362d346464632d386533622d333964356265303932663132:39376263616162332d356330652d343136362d623634302d326438656135616161636237
```

Repeat the process for each protocol found when scanning (i.e. `--protocol airplay`,
`--protocol companion` and `--protocol raop`). As of pyatv 0.14.0, file based storage is used
for credentials meaning credentials will automatically be saved to file and loaded when needed.
Once you have paired a protocol, you don't have to care about credentials anymore. For more
details about storage and settings, see [this section](../atvremote#storage-and-settings) in the
`atvremote` documentation.

### Providing Credentials

*Unless you know what you are doing, you can safely ignore this section (no longer needed).*

As of pyatv 0.14.0, manually providing credentials is no longer needed as they will be loaded
from file storage after pairing. Support for manually loading credentials is however still
supported via the `---xxx-credentials` arguments. Credentials provided via these arguments
will be written to active storage (effectively overwriting whatever credentials are
previously stored): beware!

An example of manually specifying credentials looks like this:

```raw
atvremote --id 00:11:22:33:44:54 --airplay-credentials xxxx ...
```

## Verifying Credentials and Passwords (optional)

If you want to verify what credentials and passwords are saved for a particular device,
use the `print_settings` command:

```raw
$ atvremote --id 00:11:22:33:44:54 print_settings
```
```json
{
  "info": {
    "name": "pyatv",
    "mac": "02:70:79:61:74:76",
    "model": "iPhone10,6",
    "os_name": "iPhone OS",
    "os_build": "18G82",
    "os_version": "14.7.1"
  },
  "protocols": {
    "airplay": {
      "identifier": "XX:XX:XX:XX:XX:XX",
      "credentials": "airplay_creds",
      "password": "airplay_password"
    },
    "companion": {
      "identifier": null,
      "credentials": null
    },
    "dmap": {
      "identifier": null,
      "credentials": null
    },
    "mrp": {
      "identifier": null,
      "credentials": null
    },
    "raop": {
      "identifier": "XXXXXXXXXXXX",
      "credentials": "raop_credentials",
      "password": "raop_password"
    }
  }
}
```

## Controlling

Once you have paired, you can start controlling the device and
ask for status:

```raw
$ atvremote --id 00:11:22:33:44:54  playing
Media type: Unknown
Play state: Paused
$ atvremote --id ... play
```

To see all supported commands, pass `commands` as last argument. More detailed instructions
can be found att the [atvremote](../atvremote/) page.


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

It is recommended that you read the [Documentation](../../documentation/) section to get
a better grasp of how pyatv works. Then continue with [Development](../../development)
once you are ready to write some code. Next is however a tutorial
you can follow if you want to try out creating a simple application!
