---
layout: template
title: Concepts
permalink: /documentation/concepts/
link_group: documentation
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# Concepts

There are a couple of important concepts in pyatv that is good to understand. This page will cover
the most important ones, giving them relations to how they are used in code.

# Devices and configuration

A physical device, e.g. an Apple TV 4K, is represented by a *configuration*. From a code
perspective, you find all the important pieces in {% include api i="conf.AppleTV" %}. It stores all
the necessary information about the device it represents, e.g. name, IP-address, supported protocols,
etc. You can read more about this in the following sections.

The simplest way to create a configuration is to to scan for devices, as {% include api i="pyatv.scan" %} returns a list of {% include api i="conf.AppleTV" %} objects with almost all information already filled in. You can then just pick the configuration you want and either connect to or pair with the device. Scanning and pairing is explained below.

It is also possible to manually create a configuration, although this is not the recommended way. One reason
for this is that some information is not static, e.g. port numbers and Zeroconf properties (which pyatv
heavily relies on). When using {% include api i="pyatv.scan" %}, the correct port will be automatically identified and filled in for you.
## Services and protocols

Each configuration keeps track of all the different protocols a device supports. The term *service* is also used in this context and it is exactly the same thing (this will likely be consolidated into a single term in the future, but for now they are used interchangeably).

Currently pyatv supports five protocols:

| Protocol | Purpose | Devices |
| -------- | ------- | ------- |
| Digital Media Access Protocol (DMAP) | Control device and get metadata | Apple TV <= 3 and tvOS <= 12  |
| Media Remote Protocol (MRP) | Control device and get metadata | tvOS (any version), e.g. Apple TV 4 and later |
| AirPlay | Stream video to a device | All devices |
| RAOP | Stream audio to a device | All devices |
| Companion | Currently used for app management | Apple TV 4+, HomePod in the future |

Only one protocol is needed to connect, but multiple can be used. The most appropriate protocol
will be used depending on feature (see [Protocol relaying](#protocol-relaying) for details). The
Companion protocol is however an exception as there's no unique identifier easily available for
that protocol.

There are methods in {% include api i="conf.AppleTV" %} to add and retrieve services. When using {% include api i="pyatv.scan" %}, all discovered protocols will be added automatically and all relevant information (e.g. which port is used) is stored as well. When manually creating a configuration, you have to provide this information yourself (e.g. via  {% include api i="conf.DmapService" %} for `DMAP`, and so on).

## Device Information

It is possible to extract some general information about a device,
for instance which operating system it runs or its MAC address.
There's generally no "good" way of obtaining this information, but pyatv
will pull bits and pieces from the metadata received during scanning to
make a good guess. It can also extract additional information after
connecting to the device, since some protocols provide information once
a connection has been made. The amount of device information available
can because of that differ when scanning or connecting.

## Identifiers

An important concept for pyatv is to be able to *uniquely* identify a device. You should be able to say: "I want to find and connect to *this* specific device" and pyatv should be able to do that for you. This of course means that you cannot use common identifiers, like IP-address or device name, as they can change at any time. And how many devices named "Living Room" aren't there in the world?

Instead, pyatv extracts *unique identifiers* from the different services it finds when scanning. You can then specify that you want to scan for a device with one of these identifiers and be sure that you find the device you expect. What is a unique identifier then? It can be anything, as long as it is unique of course. In case of `MRP`, it actually exposes a property called `UniqueIdentifer`. Looking at `AirPlay`, you can get the device MAC-address via a property called `deviceid`. In practice this means that a device has *multiple* identifiers and you can use *any* of them when scanning. There is a convenience property,  {% include api i="conf.AppleTV.identifier" %}, used to get an identifier. It just picks one from all of the available.

If you perform a scan with `atvremote`, you can see all the available identifiers:

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

Why is this concept so important then? Well, it *is* important that you connect to the device you expect. Especially for `MRP`, where the port might change at any time and you need to be able to find your way back (reconnect) when that happens. It also makes pyatv more reliable in environments using DHCP, which is the case in most peoples homes.

## Credentials

All protocols has some sort of "authentication" process and require *credentials* when connecting. You obtain said credentials via pairing, which is explained below. The credentials are then stored together with the protocol in a configuration.

The usual flow is:

* Perform scan
* Pick device of interest
* Connect

As of pyatv.0.14.0, persistent storage is built in. So credentials are saved and loaded automatically from
file (or somewhere else). See next section.

# Storage and Settings

To simplify handling of things like credentials, passwords and various settings, pyatv will automatically
put these into a storage module that allows for persistent storage. It is possible to implement custom
storage modules that for instance store settings in a cloud service, but pyatv also ships with a file
based storage module that will save settings in a file. This storage module is used by scripts shipped
with pyatv, e.g. [atvremote](../atvremote) and [atvscript](../atvscript).

# Scanning

To find devices, you perform a *scan* with the {% include api i="pyatv.scan" %} function. It uses [Zeroconf](https://en.wikipedia.org/wiki/Zero-configuration_networking) to discover devices, just like the Remote app/Control Center widget in iOS. You get a list of all available devices with information pre-filled and you can pretty much connect immediately (you might have to add credentials first though).

Scanning is not 100% reliable, that comes with the territory. Sometimes a device is not found, or even a service might not be found. It will happen and that is just life. Scan again and hope for the best. Usually it works just fine, so it shouldn't be that much of an issue (but bear it in mind when writing your software).

As a workaround for scanning issues, pyatv comes with support for *unicast scanning*. It allows
you to specify a list of devices to scan for. When doing so, pyatv will not rely on multicast
but rather send a request to the devices directly. This is much more reliable but of course comes
with the downside of not having devices auto discovered. You can simply try this out with `atvremote`,
please see [atvremote](../atvremote/).

Please note that unicast scanning does not work across different network as the Apple TV will ignore
packets from a different subnet. This is according to the multicast DNS specification (see chapter 5.5
in RFC 6762 [here](https://tools.ietf.org/html/rfc6762#section-5.5) in case you are interested) and is
not something that can be fixed in pyatv.

## Deep Sleep Detection

When a device is in deep sleep mode, another node on the network called a
*sleep proxy* will announce its prescence. It will also wake up the device
using Wake-On-LAN in case a particular service is requested. When scanning,
pyatv can detect if the response originates from a sleep proxy and
deduce that a device is sleeping. This is indicated via the flag
{% include api i="conf.AppleTV.deep_sleep" %}.

*Please do note that this is an experimental feature.*

# Pairing

Pairing is the process of obtaining credentials. You provide a configuration to the  {% include api i="pyatv.pair" %} method together with the protocol you want to pair. Usually you have to input a PIN code and then the credentials are returned via the `credentials` property in the service. This means that you can scan for a device, pass the configuration you got from {% include api i="pyatv.scan" %} to  {% include api i="pyatv.pair" %} and finish off by passing the same configuration to {% include api i="pyatv.connect" %}. As simple as that.

# Connecting

The final step is to connect to a device. It is done via {% include api i="pyatv.connect" %}, which sets up the connection and validates the credentials (e.g. setup encryption). You will get an error if it doesn't work. Connection attempts will be made to all protocols you have provided
configuration for (if necessary).

Prior to pyatv 0.8.0, a `protocol` parameter was used to pick protocol used as "main"
protocol (for primary interaction). This is no longer needed as the most appropriate protocol
is used automatically beacuase of [Protocol Relaying](#protocol-relaying). The flag is deprecated and unused.

# Metadata and push updates

The object you get when connecting follows the interface specified in the `interface` module. You can get *metadata*, e.g. what is currently playing via the `metadata` property. You don't have to poll the device for that information, you can use the {% include api i="interface.PushUpdater" %} interface to receive updates instantly as they happen via a callback interface.

# Features

Depending on hardware model and software, various features might be supported or not. Siri is for
instance only supported by devices running tvOS. Certain actions might not be possible to perform
due to the device state, e.g. pressing "pause" is not possible unless something is playing. In pyatv,
it's possible to obtain information about the availability of features using {% include api i="interface.Features" %}.

# Protocol Relaying

The concept of *protocol relaying* is an internal mechanism of pyatv, it is however
worth knowing the basics of it. pyatv provides a uniform API towards the
developer, removing the need to worry about underlying protocols (other than
credentials): it is automatically handled "under the hood". The relaying mechanism
allows multiple protocols to be active and will automatically "relay" interface
calls to the most suitable protocol. If two protocols implement the same
feature, the best of the two will be used. One protocol might also implement parts
of an interface, leaving the reminder to another protocol.
