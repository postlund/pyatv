---
layout: template
title: atvproxy
permalink: /documentation/atvproxy/
link_group: documentation
---
# atvproxy
Due to MRP using encryption, it's not possible to capture the traffic using
for instance Wireshark and analyze it. Since it's very hard to extract the
used keys, decryption is more or less not possible. To cicrumvent this, you
can use the MRP Proxy. It will publish a device on the network called `Proxy`,
that it is possible to pair with using the Remote app. The proxy itself will
establish a connection to the device of interest and rely messages between
your iOS device and the Apple TV. One set of encryption keys are used between
the proxy and Apple TV and another set between the proxy and your iOS device.

A private key is hardcoded into the proxy, so you can re-connect to it again
multiple times without having to re-pair. Even when restarting the proxy. This
of course means that **there is no security when using the proxy**.

*Note: This is an incubating script and may change behavior with short notice.*

# Using the Proxy

This section describes how to use the proxy.

## Device Credentials

The proxy needs credentials to your device, so pair with it using `atvremote`
unless you have not done so already:

```shell
$ atvremote --id <device id> --protocol mrp pair
```

Save the generated credentials to a file, for instance `creds`.

## Running the Proxy

In order to run the proxy you need to provide credentials (created above), an
IP address of an interface that is on the same subnet as the device as well as
device IP address and MRP port.

You can get the last two parts with `atvremote`:

```shell
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

So device IP is 10.0.0.10 and port is 49152. You can get your local IP address
with for instance `ifconfig`, refer to your operating system documentation for
this part. Lets assume it is 10.0.0.2 in this case.

To run the proxy, run:

```shell
$ atvproxy mrp `cat creds` 10.0.0.2 10.0.0.10 49152
```

Please note that the proxy is not distributed with `pyatv`, so you will have
to clone the repository to use it.

## Pairing and Looking at Traffic

Open the Remote app and select the device called `Proxy`. Use pin code `1111`
when pairing. The app should work and behave as expected and all traffic
should be logged to console.
