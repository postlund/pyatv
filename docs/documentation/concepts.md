---
layout: template
title: Concepts
permalink: /documentation/concepts/
link_group: documentation
---
# Concepts

There are a couple of important concepts in `pyatv` that is good to understand. This page will cover the most important ones, giving them relations to how they are used in code.

## Devices and configuration

A physical device, e.g. an Apple TV 4K, is represented by a *configuration*. From a code perspective, you find all the important pieces in the `pyatv.conf` module. An actual device configuration is represented by the class `pyatv.conf.AppleTV`. It stores all the necessary information about the device it represents, e.g. name, IP-address, supported protocols, etc. You can read more about this in the following sections.

The simplest way to create a configuration is to to scan for devices, as `pyatv.scan` returns a list of `pyatv.conf.AppleTV` objects with almost all information already filled in. You can then just pick the configuration you want and either connect to or pair with the device. Scanning and pairing is explained below.

It is also possible to manually create a configuration, although this is not the recommended way. One reason for this is that some information is not static. The `Media Remote Protocol` uses a randomized port that might change at any time. If the currently used port is stored in a static configuration, then the configuration will not work in case the port changes. When using `pyatv.scan`, the correct port will be automatically identified and filled in for you.

### Services and protocols

Each configuration keeps track of all the different protocols a device supports. The term *service* is also used in this context and it is exactly the same thing (this will likely be consolidated into a single term in the future, but for now they are used interchangeably).

Currently `pyatv` supports three protocols:

| Protocol | Purpose | Devices |
| -------- | ------- | ------- |
| Digital Media Access Protocol (DMAP) | Control device and get metadata | Apple TV <= 3 and tvOS <= 12  |
| Media Remote Protocol (MRP) | Control device and get metadata | tvOS (any version), e.g. Apple TV 4 and later |
| AirPlay | Stream video to a device | All devices |

At least one of `DMAP` and `MRP` must be present in order to connect to a device, otherwise `pyatv.connect` will raise an exception.

There are methods in `pyatv.conf.AppleTV` to add and retrieve services. When using `pyatv.scan`, all discovered protocols will be added automatically and all relevant information (e.g. which port is used) is stored as well. When manually creating a configuration, you have to provide this information yourself (e.g. via `pyatv.conf.DmapService` for `DMAP`, and so on).

### Identifiers

An important concept for `pyatv` is to be able to *uniquely* identify a device. You should be able to say: "I want to find and connect to *this* specific device" and `pyatv` should be able to do that for you. This of course means that you cannot use common identifiers, like IP-address or device name, as they can change at any time. And how many devices named "Living Room" arent' there in the world?

Instead, `pyatv` extracts *unique identifiers* from the different services it finds when scanning. You can then specify that you want to scan for a device with one of these identifiers and be sure that you find the device you expect. What is a unique identifier then? It can be anything, as long as it is unique of course. In case of `MRP`, it actually exposes a property called `UniqueIdentifer`. Looking at `AirPlay`, you can get the device MAC-address via a property called `deviceid`. In practice this means that a device has *multiple* identifiers and you can use *any* of them when scanning. There is a convencience property, `pyatv.conf.AppleTV.identifier`, used to get an identifier. It just picks one from all of the available.

If you perform a scan with `atvremote`, you can see all the available identifiers:

    $ atvremote scan
    ========================================
           Name: Living Room
        Address: 10.0.0.10
    Identifiers:
     - 01234567-89AB-CDEF-0123-4567890ABCDE
     - 00:11:22:33:44:55
    Services:
     - Protocol: MRP, Port: 49152, Credentials: None
     - Protocol: AirPlay, Port: 7000, Credentials: None

Why is this concept so important then? Well, it *is* important that you connect to the device you expect. Especially for `MRP`, where the port might change at any time and you need to be able to find your way back (reconnect) when that happens. It also makes `pyatv` more reliable in environments using DHCP, which is the case in most peoples homes.

### Credentials

All protocols has some sort of "authentication" process and require *credentials* when connecting. You obtain said credentials via pairing, which is explained below. The credentials are then stored together with the protocol in a configuration.

The usual flow is:

* Perform scan
* Pick device of interest
* For each protocol, get the service and insert credentials (stored externally)
* Connect

This means that `pyatv` does not store credentials for you. In the future, persistent storage will be added to `pyatv` (see issue #243), but for now you have to deal with this yourself.

One exception from this is `DMAP`, when Home Sharing is enabled. In this case, required credentials are automatically filled in and the service is ready to use. Fact is, in most cases you can talk to a device via `MRP` without using credentials at all. It is not known what the "rules" are for this though (when and what works).

## Scanning

To find devices, you perform a *scan* with the `pyatv.scan` function. It uses [Zeroconf](https://en.wikipedia.org/wiki/Zero-configuration_networking) to discover devices, just like the Remote app/Control Center widget in iOS. You get a list of all available devices with information pre-filled and you can pretty much connect immediately (you might have to add credentials first though).

Scanning is not 100% reliable, that comes with the territory. Sometimes a device is not found, or even a service might not be found. It will happen and that is just life. Scan again and hope for the best. Usually it works just fine, so it shouldn't be that much of an issue (but bear it in mind when writing your software).

As a workaround for scanning issues, `pyatv` comes with support for *unicast scanning*. It allows
you to specify a list of devices to scan for. When doing so, `pyatv` will not rely on multicast
but rather send a request to the devices directly. This is much more reliable but of course comes
with the downside of not having devices auto discovered. You can simply try this out with `atvremote`,
please see [atvremote](../atvremote/).

Please note that unicast scanning does not work across different network as the Apple TV will ignore
packets from a different subnet. This is according to the multicast DNS specification (see chapter 5.5
in RFC 6762 [here](https://tools.ietf.org/html/rfc6762#section-5.5) in case you are interested) and is
not something that can be fixed in `pyatv`.

## Pairing

Pairing is the process of obtaining credentials. You provide a configuration to the `pyatv.pair` method together with the protocol you want to pair. Usually you have to input a PIN code and then the credentials are returned via the `credentials` property in the service. This means that you can scan for a device, pass the configuration you got from `pyatv.scan` to `pyatv.pair` and finish off by passing the same configuration to `pyatv.connect`. As simple as that.

## Connecting

The final step is to connect to a device. It is done via `pyatv.connect`, which sets up the connection and validates the credentials (e.g. setup encryption). You will get an error if it doesn't work. You can provide which protocol you want to use when connecting, but you don't have to. In the latter case, `MRP` will be preferred over `DMAP` if both are available. If neither are present, an exception will be raised.

## Metadata and push updates

The object you get when connecting follows the interface specified in the `interface` module. You can get *metadata*, e.g. what is currently playing via the `metadata` property. You don't have to poll the device for that information, you can use the `interface.PushUpdater` interface to receive updates instantly as they happen via a callback interface.
