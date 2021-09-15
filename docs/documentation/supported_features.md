---
layout: template
title: Supported Features
permalink: /documentation/supported_features/
link_group: documentation
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# Supported Features

`pyatv` supports multiple protocols, each of them providing a certain set of features.
This page aims to summarize the provided feature set, what each protocol supports as
well as limitations.

In general, as a developer you should use {% include api i="interface.Features" %} to
verify if a particular feature is available or not and refrain from making other assumptions.
See this page as informational.

*This page is still work-in-progress and a bit inconsistent. State will improve over time.*

# Some things worth knowing...

Things change. Constantly. Here are a few things worth knowing about the protocols:

* The DMAP protocol (suite) stems from iTunes and was used on all Apple TVs until tvOS 13, i.e. all versions of Apple TV 3 and earlier as well as Apple TV 4 (and later) until tvOS 13 was released. It means it's not widely used anymore, other than with older devices. It can be used to control the Music app in macOS {% include issue no="1172" %}.
* The MRP protocol was introduced in tvOS when the Apple TV 4 was introduced. In tvOS 15, it was demoted from a separate protocol (it used to have it's own Remote app as well as Zeroconf service, `_mediaremotetv._tcp.local`) and moved to a special stream type in AirPlay 2 instead. Devices running tvOS 15 (beta or later) require AirPlay to be set up to function properly.
* tvOS 10.2 enforced "device authentication" for AirPlay to function. This is referred to as "legacy pairing" and is only used to verify a connection, it does not enforce any encryption. It also works for RAOP. AirPlay 2 however require "HAP" (HomeKit) authentication, which enforce encryption. Only legacy pairing is supported for RAOP in pyatv at the moment (as encryption has not been implemented for HAP based authentication).

# Feature List

This is the general feature list provided by the external interface.

| **Feature**                                                     | **Links** |
| --------------------------------------------------------------- | --------- |
| Automatic discovery of devices (zeroconf/Bonjour)               | [Concept](../concepts/#scanning), [Doc](../../development/scan_pair_and_connect/#scanning), {% include api i="pyatv.scan" %}
| --------------------------------------------------------------- | --------- |
| Device Metadata (e.g. operating system and version)             | [Concept](../concepts/#device-information), [Doc](../../development/device_info), {% include api i="interface.DeviceInfo" %}
| --------------------------------------------------------------- | --------- |
| Push updates                                                    | [Concept](../concepts/#metadata-and-push-updates), [Doc](../../development/listeners/#push-updates), {% include api i="interface.PushUpdater" %}
| --------------------------------------------------------------- | --------- |
| Remote control pairing                                          | [Concept](../concepts/#pairing), [Doc](../../development/scan_pair_and_connect/#pairing), {% include api i="interface.PairingHandler" %}
| --------------------------------------------------------------- | --------- |
| List supported features                                         | [Concept](../concepts/#features), [Doc](../../development/features), {% include api i="interface.Features" %}
| --------------------------------------------------------------- | --------- |
| AirPlay stream URL (including local files)                      | [Doc](../../development/stream), {% include api i="interface.Stream" %}
| --------------------------------------------------------------- | --------- |
| Playback controls (play, pause, next, stop, etc.)               | [Doc](../../development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Navigation controls (select, menu, top_menu, arrow keys)        | [Doc](../../development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Different input actions (tap, double tap, hold)                 | [Doc](../../development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Fetch artwork                                                   | [Doc](../../development/metadata/#artwork), {% include api i="interface.Metadata.artwork" %}
| --------------------------------------------------------------- | --------- |
| Currently playing (e.g. title, artist, album, total time, etc.) | [Doc](../../development/metadata), {% include api i="interface.Metadata" %}
| --------------------------------------------------------------- | --------- |
| App used for playback                                           | [Doc](../../development/metadata/#active-app), {% include api i="interface.App" %}
| --------------------------------------------------------------- | --------- |
| Media type and play state                                       | [Doc](../../development/metadata), {% include api i="interface.Metadata" %}
| --------------------------------------------------------------- | --------- |
| Change media position                                           | [Doc](../../development/metadata), {% include api i="interface.Metadata.set_position" %}
| --------------------------------------------------------------- | --------- |
| Shuffle and repeat                                              | [Doc](../../development/metadata), {% include api i="interface.Metadata.set_shuffle" %}, {% include api i="interface.Metadata.set_repeat" %}
| --------------------------------------------------------------- | --------- |
| Volume Controls                                                 | [Doc](../../development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Power management                                                | [Doc](../../development/power_management), {% include api i="interface.Power" %}
| --------------------------------------------------------------- | --------- |
| Deep Sleep Detection                                            | [Concept](../concepts/#deep-sleep-detection), [Doc](../../development/scan_pair_and_connect/#scanning), {% include api i="pyatv.scan" %}
| --------------------------------------------------------------- | --------- |
| Launch application                                              | [Doc](../../development/apps), {% include api i="interface.Apps" %}
| --------------------------------------------------------------- | --------- |
| List installed apps                                             | [Doc](../../development/apps), {% include api i="interface.Apps" %}

# Core Features

Some features are provided generally by pyatv and not bound to any particular protocol. These
*core* features include:

* Automatic service discovery with zeroconf ([Scanning](../concepts#scanning))
* Device information via information from service discovery ([Device Information](../concepts#device-information))
* Set up of protocols based on provided configuration
* Callbacks when connection is lost ([Device Updates](../../development/listeners#device-updates))

# Protocols per Device

Here is a summary of what protocols various devices support:

| **Protocol**    | **Devices** |
| --------------- | ----------- |
| AirPlay (video) | Apple TV (any)
| Companion       | Apple TV 4(K), HomePod (mini)
| DMAP            | Apple TV 2/3
| MRP             | Apple TV 4(K), tvOS <=14
| RAOP            | Apple TV, AirPort Express gen 2, HomePod (mini), 3rd party speakers

`pyatv` might still not support a particular combination of protocol or hardware, please
refer to protocol details below.

# Protocols Details

This section provides details on what each protocols support and current limitations.

## AirPlay

This protocol concerns the "video" parts of the AirPlay protocol suite, e.g. video streaming,
screen mirroring and image sharing.

### Supported Features

* Legacy pairing for older devices (e.g. Apple TV 3)
* HAP based for AirPlay 2 features (only used for remote control)
* Playing files with {% include api i="interface.Stream.play_url" %}
* Tunneling of MRP over AirPlay 2 to support tvOS 15 and the HomePod

### Limitations and notes

* Very limited support for this protocol so far. More features will be added in the future.
* Does not implement support for {% include api i="interface.DeviceListener" %} and will
  *not* trigger `connection_lost` or `connection_closed` when used stand-alone.

## Companion

This protocol is a low-overhead protocol supporting remote control features, HID (touch control),
app and power related functions.

### Supported Features

* Pairing is supported as long as target device can show a PIN code, e.g. Apple TV but not HomePod or a Mac
* All features in the app interface ({% include api i="interface.Apps" %})
* Turn on/off device ({% include api i="interface.Power.turn_on" %},
  {% include api i="interface.Power.turn_off" %})
* Remote control (see {% include api i="interface.RemoteControl" %} for supported buttons)

### Limitations and notes

* Early stage of development - not many features supported
* No persistent connection at the moment, so events are not supported
* Does not implement support for {% include api i="interface.DeviceListener" %} and will
  *not* trigger `connection_lost` or `connection_closed` when used stand-alone.

## DMAP

This protocol is the same protocol (suite) used by iTunes in the past and mainly deals with
metadata and playback. It is used by legacy devices, like Apple TV 3 and also to control the
Music app in macOS.

### Supported Features

* Pairing
* Device Metadata
* Push Updates
* Features interface
* Remote control (see {% include api i="interface.RemoteControl" %} for supported buttons)
* Artwork
* Playing metadata
* Device and playback state
* Shuffle and repeat
* Volume control

### Limitations and notes

* The features interface will make educated gueeses on what is supported as no proper
  support for this exists in the protocol
* No support for different tap actions in conjunction with button (e.g. double tap or
  hold) as it's not supported by the protocol
* It is possible to discover and control a Music app running on macOS (except for 11.4,
  likely a bug).
## MRP

This protocol was introduced in tvOS and superseeds DMAP. It has the same features as well
as new ones, like notion of apps and game pad controls.

### Supported Features

* Pairing
* Device Metadata
* Push Updates
* Features interface
* Remote control including different input actions (see {% include api i="interface.RemoteControl" %} for supported buttons)
* Artwork
* Playing metadata
* Device and playback state
* Shuffle and repeat
* Volume controls
* Current playing app
* Power management

### Limitations and notes

* Power management is not very robust (relies on navigating and pressing buttons).
  The Companion protocol provides better support and it is recommended to set up both
  concurrently for best experience.

## RAOP

This protocols corresponds to the audio streaming part of AirPlay (previously known as
AirTunes).

### Supported Features

* Stream files with {% include api i="interface.Stream.stream_file" %}
* Metadata is read from file and sent to receiver (artist, album and title)
* Supports WAV, MP3, FLAG and OGG as file format (also for metadata)
* Metadata (device state, media type, title, artist, album, position, total_time)
* Push Updates
* Volume controls (volume level, set_volume, volume_up, volume_down)
* One stream can be played at the time (second call raises {% include api i="exceptions.InvalidStateError" %})
* If the device requires pairing, e.g. Apple TV 4 or later, pairing must be performed and credentials provided. AirPlay credentials obtained prior to version 0.8.2 are compatible, later versions require re-pairing specifically with RAOP.

### Limitations and notes

* Metadata and push updates only reflect what pyatv is currently playing as there
  seems to not be possible to get current play state from an AirPlay receiver (see next bullet for exceptions).
* It is possible to obtain metadata in some cases by combining protocols, e.g. by pairing RAOP in conjunction with AirPlay or MRP for instance. On the HomePod, the AirPlay protocol will provide metadata by tunneling the MRP protocol.
* Devices requiring password are only supported when using the RAOP protocol
* Remote control commands does not work (except for volume_up and volume_down),
  e.g. play or pause {% include issue no="1068" %}
* Does not implement support for {% include api i="interface.DeviceListener" %} and will
  *not* trigger `connection_lost` or `connection_closed` when used stand-alone.

### Verified Devices

Audio streaming has been verified to work with these devices:

* Apple TV 3 (v8.4.4)
* Apple TV 4K gen 1 (v14.5)
* HomePod Mini (v14.5)
* AirPort Express (v7.8.1)
* Yamaha RX-V773 (v1.98)

The following 3rd party software receivers have also been verified to work:

* [shairport-sync](https://github.com/mikebrady/shairport-sync) (v3.3.8)

If you have verified another device or receiver, please update the list by pressing
*Edit this page* below and opening a pull request.
