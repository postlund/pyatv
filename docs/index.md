---
layout: template
title: pyatv
---
# Main Page

This is a python 3.6 (or later) library for controlling and querying information from an Apple TV. It is built
upon asyncio and supports most of the commands that the regular Apple Remote app does and more!

To install, use `pip`:

    pip install {{ site.pyatv_version }}

This library is licensed under the MIT license.

# Where to start?

As pyatv is a library, it is mainly aimed for developers creating applications that can interact
with Apple TVs. However, pyatv ships with a powerful command line application that is useful for
normal users as well.

So, head over to [Getting started](getting-started) to get going!

If you need help or have questions, check out the [Support](support) page instead.

In case you have developed for pyatv 0.3.x before, there's a short migration guide
[here](support/migration) that will help you port your code to 0.4.x or later.

# Features

Here is the feature list by protocol (DMAP = devices not running tvOS, MRP = Apple TV 4 and later):

| **Feature**                                                     | **DMAP** | **MRP**   | **Links** |
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Automatic discovery of devices (zeroconf/Bonjour)               | Yes      | Yes       | [Concept](documentation/concepts/#scanning), [Doc](development/scan_pair_and_connect/#scanning), {% include api i="pyatv.scan" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Device Metadata (e.g. operating system and version)             | Yes*     | Yes*      | [Concept](documentation/concepts/#device-metadata), [Doc](development/device_info), {% include api i="interface.DeviceInfo" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Push updates                                                    | Yes      | Yes       | [Concept](documentation/concepts/#metadata-and-push-updates), [Doc](development/listeners/#push-updates), {% include api i="interface.PushUpdater" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Remote control pairing                                          | Yes      | Yes       | [Concept](documentation/concepts/#pairing), [Doc](development/scan_pair_and_connect/#pairing), {% include api i="interface.PairingHandler" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| List supported features                                         | Yes**    | Yes       | [Concept](documentation/concepts/#features), [Doc](development/features), {% include api i="interface.Features" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| AirPlay stream URL (including local files)                      | Yes      | Yes       | [Doc](development/airplay), {% include api i="interface.Stream" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Playback controls (play, pause, next, stop, etc.)               | Yes      | Yes       | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Navigation controls (select, menu, top_menu, arrow keys)        | Yes      | Yes       | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- |--------- | --------- | --------- |
| Different input actions (tap, double tap, hold)                 | No       | Yes       | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- |--------- | --------- | --------- |
| Fetch artwork                                                   | Yes      | Yes       | [Doc](development/metadata/#artwork), {% include api i="interface.Metadata.artwork" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Currently playing (e.g. title, artist, album, total time, etc.) | Yes      | Yes       | [Doc](development/metadata), {% include api i="interface.Metadata" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| App used for playback                                           | No       | Yes       | [Doc](development/metadata/#active-app), {% include api i="interface.App" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Media type and play state                                       | Yes      | Yes       | [Doc](development/metadata), {% include api i="interface.Metadata" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Change media position                                           | Yes      | Yes       | [Doc](development/metadata), {% include api i="interface.Metadata.set_position" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Shuffle and repeat                                              | Yes      | Yes       | [Doc](development/metadata), {% include api i="interface.Metadata.set_shuffle" %}, {% include api i="interface.Metadata.set_repeat" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Volume Controls                                                 | Yes      | Yes       | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Power management                                                | No       | Yes       | [Doc](development/power_management), {% include api i="interface.Power" %}
| --------------------------------------------------------------- | -------- | --------- | --------- |
| Deep Sleep Detection                                            | Yes***   | Yes***    | [Concept](documentation/concepts/#deep-sleep-detection), [Doc](development/scan_pair_and_connect/#scanning), {% include api i="pyatv.scan" %}

*\* Some restrictions apply, see section "Device Metadata" [here](documentation/concepts/#device-metadata) page.*

*\*\* Limited support due to restrictions in protocol.*

*\*\*\* Experimental feature (not fully tested)*

There are also few utility scripts bundled with `pyatv` that makes it easy to try the library
out. Check out [atvremote](documentation/atvremote), [atvproxy](documentation/atvproxy) and
[atvscript](documentation/atvscript).

# Who is making this?

I, Pierre Ståhl, is the lead developer and maintainer of this library. It is a hobby
project that I put a few hours in every now and then to maintain. If you find it useful,
please consider to sponsor me! :heart:

Of course, this is an open source project which means I couldn't do it all by myself.
I have created dedicated page for [acknowledgements](support/acknowledgements)!
