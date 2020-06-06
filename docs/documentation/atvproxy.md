---
layout: template
title: atvproxy
permalink: /documentation/atvproxy/
link_group: documentation
---
# atvproxy

The `atvproxy` is a helper script used to intercept traffic by doing versions
of MITM "attacks" (it's not *really* attacks). It can help when reverse engineering
a new protocol or exploring new features in an already well-known protocol,
like MRP.

Currently this script support MRP, for which it can fully output decrypted
messages. It also has a "relay" mode, which just sits between two devices and
prints the trafffic. The latter is meant for simplifying reverse engineering
of new protocols.

*Note: This is an incubating script and may change behavior with short notice.
It also depends on the internal API, meaning you should not use it as a
reference for your own projects.*

# MRP Proxy

Due to MRP using encryption, it's not possible to capture the traffic using
for instance Wireshark and analyze it. Since it's very hard to extract the
used keys, decryption is more or less not possible. To cicrumvent this, you
can use the MRP Proxy. It will publish a proxy device on the network,
that it is possible to pair with using the Remote app. The proxy itself will
establish a connection to the device of interest and relay messages between
your iOS device and the Apple TV. One set of encryption keys are used between
the proxy and Apple TV and another set between the proxy and your iOS device.

A private key is hardcoded into the proxy, so you can re-connect to it again
multiple times without having to re-pair. Even when restarting the proxy. This
of course means that **there is no security when using the proxy**.

## Device Credentials

The proxy needs credentials to your device, so pair with it using `atvremote`
unless you have not done so already:

```shell
$ atvremote --id <device id> --protocol mrp pair
```

Save the generated credentials to a file, for instance `creds`.

## Running the Proxy

In order to run the proxy you need to provide credentials (created above) and
IP address of the device. You can find the address by scanning:

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

To run the proxy, run:

```shell
$ atvproxy mrp `cat creds` 10.0.0.10
```

### Manual Settings

The script will automatically try to figure out which MRP port to use with
unicast scanning, IP address of a local interface on the same network as the
device as well as the device name. You can however provide these parameters
manually with `--remote-port`, `--local-ip` and `--name`.

## Pairing and Looking at Traffic

Open the Remote app and select the device called `XXX Proxy`, where `XXX`
is the name of your Apple TV. Use pin code `1111` when pairing. The app should
work and behave as expected and all traffic should be logged to console.

# Relay Proxy

Sometimes it's convenient to be able to look at network traffic when reverse
engineering a protocol. Wireshark is really good for that, but requires a tap
somewhere to see the traffic (not always easy). To simplify this, the relay
proxy can be used. It sets up arbitrary zeroconf service (e.g. you can
specify the properties manually) and combines it with a local server that will
send all traffic to another host and relay data back from the same host.
Basically man-in-the-middle (MITM). It does nothing with the data other than
relaying it between the two hosts and printing it to the console. So it is
merely designed for looking at small data exchanges to discover patterns.

## Running the Relay

You need a couple of things to run the relay proxy:

* IP address and port of the target hosts
* IP address of a local interface on the same network as the target
* The name to be used when publishing the service, e.g. *ATV Relay*
* Zeroconf service, e.g. *_mediaremotetv._tcp.local.*
* Properties to include with the service (one or more key-value pairs)

It is easiest to run `atvproxy relay --help` to see the order. See examples
below for some inspiration.

*Note: Only string values are supported for properties at this stage.*

## Examples

Here is an example for MRP:

```shell
$ atvproxy -p ModelName="Apple TV" \
AllowPairing=YES \
BluetoothAddress=00:11:22:33:44:55 \
macAddress=aa:bb:cc:dd:ee:ff \
Name=Vardagsrum \
UniqueIdentifier=46CE1111-3B67-48EF-AAB1-77BCF67C886A \
SystemBuildVersion=17L256 \
LocalAirPlayReceiverPairingIdentity=7C7878A9-9AC2-7D93-852F-A91312B98AF9 \
-- 10.0.10.254 10.0.10.81 49152 TestATV _mediaremotetv._tcp.local.
```

The local IP (on the computer running `atvproxy` is 10.0.10.254), IP
address and MRP port is 10.0.10.81 and 49152. When browsing for devices,
it will be called `TestATV`.

Note that *--* is used to separate properties from other configuration
values.