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

# Feature List

This is the general feature list provided by the external interface.

| **Feature**                                                     | **Links** |
| --------------------------------------------------------------- | --------- |
| Automatic discovery of devices (zeroconf/Bonjour)               | [Concept](documentation/concepts/#scanning), [Doc](development/scan_pair_and_connect/#scanning), {% include api i="pyatv.scan" %}
| --------------------------------------------------------------- | --------- |
| Device Metadata (e.g. operating system and version)             | [Concept](documentation/concepts/#device-metadata), [Doc](development/device_info), {% include api i="interface.DeviceInfo" %}
| --------------------------------------------------------------- | --------- |
| Push updates                                                    | [Concept](documentation/concepts/#metadata-and-push-updates), [Doc](development/listeners/#push-updates), {% include api i="interface.PushUpdater" %}
| --------------------------------------------------------------- | --------- |
| Remote control pairing                                          | [Concept](documentation/concepts/#pairing), [Doc](development/scan_pair_and_connect/#pairing), {% include api i="interface.PairingHandler" %}
| --------------------------------------------------------------- | --------- |
| List supported features                                         | [Concept](documentation/concepts/#features), [Doc](development/features), {% include api i="interface.Features" %}
| --------------------------------------------------------------- | --------- |
| AirPlay stream URL (including local files)                      | [Doc](development/stream), {% include api i="interface.Stream" %}
| --------------------------------------------------------------- | --------- |
| Playback controls (play, pause, next, stop, etc.)               | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Navigation controls (select, menu, top_menu, arrow keys)        | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Different input actions (tap, double tap, hold)                 | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Fetch artwork                                                   | [Doc](development/metadata/#artwork), {% include api i="interface.Metadata.artwork" %}
| --------------------------------------------------------------- | --------- |
| Currently playing (e.g. title, artist, album, total time, etc.) | [Doc](development/metadata), {% include api i="interface.Metadata" %}
| --------------------------------------------------------------- | --------- |
| App used for playback                                           | [Doc](development/metadata/#active-app), {% include api i="interface.App" %}
| --------------------------------------------------------------- | --------- |
| Media type and play state                                       | [Doc](development/metadata), {% include api i="interface.Metadata" %}
| --------------------------------------------------------------- | --------- |
| Change media position                                           | [Doc](development/metadata), {% include api i="interface.Metadata.set_position" %}
| --------------------------------------------------------------- | --------- |
| Shuffle and repeat                                              | [Doc](development/metadata), {% include api i="interface.Metadata.set_shuffle" %}, {% include api i="interface.Metadata.set_repeat" %}
| --------------------------------------------------------------- | --------- |
| Volume Controls                                                 | [Doc](development/control), {% include api i="interface.RemoteControl" %}
| --------------------------------------------------------------- | --------- |
| Power management                                                | [Doc](development/power_management), {% include api i="interface.Power" %}
| --------------------------------------------------------------- | --------- |
| Deep Sleep Detection                                            | [Concept](documentation/concepts/#deep-sleep-detection), [Doc](development/scan_pair_and_connect/#scanning), {% include api i="pyatv.scan" %}
| --------------------------------------------------------------- | --------- |
| Launch application                                              | [Doc](development/apps), {% include api i="interface.Apps" %}
| --------------------------------------------------------------- | --------- |
| List installed apps                                             | [Doc](development/apps), {% include api i="interface.Apps" %}

# Core Features

Some features are provided generally by pyatv and not bound to any particular protocol. These
*core* features include:

* Automatic service discovery with zeroconf ([Scanning](../concepts#scanning))
* Device information via information from service discovery ([Device Metadata](../concepts#device-metadata))
* Callbacks when connection is lost ([Device Updates](../../development/listeners#device-updates))

# Protocols per Device

Here is a summary of what protocols various devices support:

| **Protocol**    | **Devices** |
| --------------- | ----------- |
| AirPlay (video) | Apple TV (any)
| Companion       | Apple TV 4(K), HomePod (mini)
| DMAP            | Apple TV 2/3
| MRP             | Apple TV 4(K)
| RAOP            | Apple TV, AirPort Express, HomePod (mini), 3rd party speakers

`pyatv` might still not support a particular combination of protocol or hardware, please
refer to protocol details below.

# Protocols Details

This section provides details on what each protocols support and current limitations.

## AirPlay

This protocol concerns the "video" parts of the AirPlay protocol suite, e.g. video streaming,
screen mirroring and image sharing.

### Supported Features

* Pairing
* Playing files with {% include api i="interface.Stream.play_url" %}

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

### Limitations and notes

* Early stage of development - not many features supported
* No persistent connection at the moment, so events are not supported
* Does not implement support for {% include api i="interface.DeviceListener" %} and will
  *not* trigger `connection_lost` or `connection_closed` when used stand-alone.

## DMAP

This protocol is the same protocol (suite) used by iTunes in the past and mainly deals with
metadata and playback. Only used by legacy devices, like the Apple TV 3.

### Supported Features

* Pairing
* Device Metadata
* Push Updates
* Features interface
* Remote control
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

## MRP

This protocol was introduced in tvOS and superseeds DMAP. It has the same features as well
as new ones, like notion of apps and game pad controls.

### Supported Features

* Pairing
* Device Metadata
* Push Updates
* Features interface
* Remote control including different input actions
* Artwork
* Playing metadata
* Device and playback state
* Shuffle and repeat
* Volume control
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
* If the device requires pairing, e.g. Apple TV 4 or later, the same pairing
  procedure and credentials as AirPlay is to be used. If AirPlay credentials
  are present, they will be used if no RAOP credentials are given.

### Limitations and notes

* Metadata and push updates only reflect what pyatv is currently playing as there
  seems to not be possible to get current play state from an AirPlay receiver
* Devices requiring password are not supported
* Remote control commands does not work (except for volume_up and volume_down),
  e.g. play or pause {% include issue no="1068" %}
* Does not implement support for {% include api i="interface.DeviceListener" %} and will
  *not* trigger `connection_lost` or `connection_closed` when used stand-alone.

### Verified Devices

Audio streaming has been verified to work with these devices:

* Apple TV 3 (v8.4.4)
* HomePod Mini (v14.5)
* AirPort Express (v7.8.1)
* Yamaha RX-V773 (v1.98)

The following 3rd party software receivers have also been verified to work:

* [shairport-sync](https://github.com/mikebrady/shairport-sync) (v3.3.8)

If you have verified another device or receiver, please update the list by pressing
*Edit this page* below and opening a pull request.
