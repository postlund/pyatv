---
layout: template
title: FAQ
permalink: /support/faq/
link_group: support
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# General Questions

## My device is not found when scanning?

See [Troubleshooting](../troubleshooting/) for some hints on locating the issue.

## My Apple TV turns on every time I send a command with atvremote (it turns on my TV, receiver, etc). How do I disable that?

You can't. The device will turn itself on whenever a request is made to it
(and of course `atvremote` does that). It is how Apple has designed it. The only
thing you can do is to disable CEC so that your other devices doesn't wake up too.
That's about it.

## Is it possible to "see" if a device is turned on before sending a command?

"Yes". Since version 0.7.0 it is possible to see (when scanning) if a device
is in deep sleep mode. A device can however be asleep (appear off) without being
in deep sleep, so it's not fully reliable. This is still also considered an
experimental feature.

## Why is all or some metadata missing when I am playing some media on my device?

Sometimes the Apple TV does not provide any metadata and in those cases there
is no metadata available. Unfortunately, there is nothing that can be done about
this. If you, however, can see for example a title or artwork in the
*Remote app* on your iPhone or iPad, then something is likely wrong. In this
case, you should write a bug report.

## Streaming with AirPlay does not work. It says "This AirPlay connection requires iOS 7.1 or later, OS X 10.10 or later, or iTunes 11.2 or later." on the screen. What's wrong?

The device authentication process has now been reversed engineered and implemented
in pyatv. In order to get rid of this message, you must perform AirPlay pairing with
the device and use the obtained credentials with playing media. See
[pairing with atvremote](../..//documentation/atvremote).

## When I scan, other devices like AirPlay speakers and iTunes libraries show up. Why is that?

~~Apple has re-used several protocols across different products. AirPlay is AirPlay and
there's no practical difference if it's on a speaker or an Apple TV: it's the same
thing. Because of this, they might show up in the scan results. In the future some
devices might be filtered (like pure AirPlay devices, since you can't connect to them
anyway), but for now they are there.~~

This is no longer the case. From pyatv 0.5.0, pure AirPlay devices are no longer included in the scan result.

## Is there a synchronous version of the library?

No, the library is implemented with asyncio, introduced in python 3.4. A plain
synchronous library is currently out of scope and not a priority.

## Unicast scanning does not work if my device is on a different subnet (NonLocalSubnetError), why?

To obtain the information pyatv needs to connect to a device, Zeroconf is used
for "scanning". Zeroconf is designed to only work within the local network. If a
request is received from a host on a different subnet it will be silently dropped. This
is the reason why it is not possible to use unicast scanning between subnets and
it's not possible to work around this.

If you need to keep the network separation, you can still rely on regular scanning
and configure an mDNS repeater (try "mdns repeater" on your favorite search engine).

## It is really slow to send commands to the device with atvremote. It takes several seconds, is pyatv really this slow?

From version 0.8.x, scanning for a particular device has been optimized. Normally a scan
is performed for a specific time and filtering done after that. This has been changed
so that scanning is aborted once the requested device has been found, making the discovery
phase a lot shorter.

The information below reflects all versions prior to 0.8.x (although everything except
for bullet two applies to 0.8.x as well):

It is a common misconception that pyatv is slow because atvremote takes its time.
The fact is this: *every* time you run atvremote, this happens:

1. pyatv and its dependencies are loaded into memory
2. A scan is performed with a default timeout of three seconds
3. A (TCP) connection is established to the device
4. Authentication is performed and encryption enabled
5. Command is executed
6. Connection is torn down

Once a connection has been established and authentication performed, issuing commands
are more or less instant. But since atvremote exits after executing a command, everything
must be done from the beginning again for the next command. This behavior is by definition
slow.

To get instantaneous feedback, the connection must remain active and commands sent by
re-using the connection. This can be done in many ways, e.g. by implementing a daemon
that maintains the connection in the background and receives commands via some interface
(maybe REST). Currently, pyatv does not ship with such a tool since it's first and foremost
a library. You will have to implement a solution that fits your needs.

A small tip is to use unicast scanning to speed up the process (to at least make the situation
better):

```shell
$ atvremote -s 10.0.0.3 stop
```

## I get an error about "ed25519 is not supported", how can I fix that?

For cryptography, pyatv relies on the `cryptography` package. This package
wraps crypto routines in OpenSSL, so if a given routine is missing then that
crypto routine simply won't work.

For MRP this means that you need to have decently new version of OpenSSL with
support for ed25519 compiled in. Otherwise you get this error:

```raw
pyatv.exceptions.PairingError: ed25519 is not supported by this version of OpenSSL.
```

It is still a bit unclear which version of OpenSsl that added support for ed25519,
so grab the latest one. Please refer to your operating system community on
how to upgrade.

## My Apple TV crashed/lost network connection/... and the connection in pyatv just hangs, why?

To discover dangling connections, i.e. when the other device disappears without
properly closing the connection, TCP keepalives are used. The support for this
in python varies on different platforms. It might be the case that your operating
system or version of python does not support TCP keep-alive properly, in which
case this is a problem pyatv currently does not solve.

A log point will indicate if configuration of keep-alive succeeded:

```raw
2020-06-10 22:31:28 INFO: Configured keep-alive on <asyncio.TransportSocket fd=8, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=6, laddr=('10.0.10.254', 60849), raddr=('10.0.10.81', 49153)> (Linux)
```

Or a warning if not supported:

```raw
2020-06-10 22:32:28 WARNING: Keep-alive not supported: System does not support keep-alive
```

Most versions of macOS and Linux should work with no problems. For Windows, you need at
least Windows 10 build 1709.

pyatv.

# When using pyatv on a Raspberry pi, e.g running atvremote, I get "Illegal instruction". How do I fix that?

It seems like the wheels (prebuilt binaries) for miniaudio does not work properly. You can fix this
by manually uninstalling miniaudio and building it from source:

```shell
pip uninstall miniaudio
pip install --no-binary :all: miniaudio
```

You might have to install some additional system packages (like a C-compiler) for this.

Reported in this issue: {% include issue no="1249" %}

# Known Issues

Some apps behave in unexpected ways that are out of control of this library (including general things in tvOS), i.e. nothing can be done in pyatv to circumvent these behaviors. This sections lists the known ones. If you are experiencing issues with an app, feel free to add it here (write an issue, make a PR or just press *Edit this page* at the bottom of this page).

## Idle state during previews

The deveice generally moves to {% include api i="const.DeviceState.Idle" %} when playing trailers or "what's next"
sequences. For now, there's no known solution to circumvent this. This might change in the
future, so a solution should be re-evaluate every now and then.

Reported in these issues: {% include issue no="994" %}

## Power state is not updated when using external speaker (e.g. HomePod)

The power state is derived from the number of connected output devices (as there seems to be no
"real" power state). This however fails when using an external spekar for audio, e.g. a HomePod,
as the connection seems to remain active even when putting the Apple TV to sleep. So it is not
possible to detect if a device is sleeping or nog in these cases. No solution or workaround is
known so far.

Reported in these issues: {% include issue no="958" %}

## Netflix (com.netflix.Netflix)

* Previews in the main menu yields play status updates (usually with what was played most recently,
  not content of the preview). A workaround is to disable these previews, see
  [this](https://help.netflix.com/sv/node/2102) page.
* During episode intros and "next episode" screens the device goes to idle state.

## com.cellcom.cellcomtvappleos

Does not seem to report any state. This app likely implements its own media player, bypassing
the metadata management used by MRP meaning that no information is available when this app is used.

Link to app in App Store: https://apps.apple.com/il/app/%D7%A1%D7%9C%D7%A7%D7%95%D7%9D-tv/id1159313682

Reported in these issues: {% include issue no="1160" %}

## playbackRate issue

Some apps incorrectly set the metadata item "playbackRate" as 0.0 instead of 1.0 which causes
pyatv to report the media as paused at all times. A workaround for this issue has been pushed at
{% include issue no="673" %}, seeking, fast-forwarding or rewinding will still return a "paused" state.

Apps known to cause this issue are listed below

* Amazon Prime Video (com.amazon.aiv.AIVApp)
* BBC iPlayer (uk.co.bbc.iplayer)
