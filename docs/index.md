---
layout: template
title: pyatv
---
# Main Page

This is a python3 library for controlling and querying information from an Apple TV. It is built
upon asyncio and supports most of the commands that the regular Apple Remote app does and more!

Support for tvOS is still in early stages, but feel free to give it a spin:

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

| **Feature**                                                     | **DMAP** | **MRP**   |
| --------------------------------------------------------------- | -------- | --------- |
| Automatic discovery of devices (zeroconf/Bonjour)               | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Device Metadata (e.g. operating system and version)             | Yes*     | Yes*      |
| --------------------------------------------------------------- | -------- | --------- |
| Push updates                                                    | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Remote control pairing                                          | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| List supported features                                         | Yes**    | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| AirPlay stream URL (including tvOS 10.2+)                       | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Playback controls (play, pause, next, stop, etc.)               | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Navigation controls (select, menu, top_menu, arrow keys)        | Yes      | Yes       |
| --------------------------------------------------------------- |--------- | --------- |
| Fetch artwork                                                   | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Currently playing (e.g. title, artist, album, total time, etc.) | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| App used for playback                                           | No       | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Media type and play state                                       | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Change media position                                           | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Shuffle and repeat                                              | Yes      | Yes       |
| --------------------------------------------------------------- | -------- | --------- |
| Power management                                                | No       | Yes       |

*\* Some restrictions apply, see section "Device Metadata" [here](documentation/concepts/#device-metadata) page.*

*\*\* Limited support due to restrictions in protocol.*

There are also few utility scripts bundled with `pyatv` that makes it easy to try the library
out. Check out [atvremote](documentation/atvremote), [atvproxy](documentation/atvproxy) and
[atvscript](documentation/atvscript).

# Who is making this?

I, Pierre Ståhl, is the lead developer and maintainer of this library. It is a hobby
project that I put a few hours in every now and then to maintain. If you find it useful,
please consider to sponsor me! :heart:
