---
layout: template
title: Protocols
permalink: /documentation/protocols/
link_group: documentation
---
# Protocols

If you want to extend `pyatv`, a basic understanding of the used protocols helps a lot. This
page aims to give a summary of the protocols and how they work (to the extent we know, since
they are reverse engineered). Focus are on the parts the are relevant and implemented in
`pyatv`.

# Digital Media Access Protocol (DMAP)

DMAP covers the suite of protocols used by various Apple software (e.g. iTunes)
to share for instance music. There are already a bunch of sites and libraries describing
and implementing these protocol, please see the reference further down. This section will
focus on the technical aspects used to implement DMAP/DACP/DAAP in pyatv.

At its core, DMAP is basically a HTTP server (running on port 3689) that responds to specific
commands and streams events back to the client. Data is requested using GET and POST with
special URLs. Data in the responses is usually in a specific binary format, but depending on
the request it can also be something else (like a PNG file for artwork). The
binary protocol will be explained first, as that makes it easier to understand
the requests.

## DMAP Binary Format

The binary format is basically TLV data where the tag is a 4 byte ASCII-string,
the length is a four byte unsigned integer and the data is, well, data. Type
and meaning of a specific TLV is derived from the tag. So we must know which
tags are used, how large they are and what they mean. Please note that Length
is length of the data, so key and length are not included in this size.

A TLV looks like this:

| Key (4 bytes) | Length (4 bytes) | Data (Length bytes |

Multiple TLVs are usually embedded in one DMAP data stream and TLVs may also
be nested, to form a tree:

    TLV1
    |
    +---TLV2
    |   |
    |   + TLV3
    |
    +---TLV4
        |
        + TLV5

As stated earlier, we must already know if a tag is a "container" (that
contains other TLVs) or not. It cannot easily be seen on the data itself.
A container usually has more resemblance to an array than a dictionary
since multiple TLVs with the same key often occurs.

All tags currently known by `pyatv` is defined in `pyatv.dmap.tag_definitions`.

## Decoding Example

Lets assume that we know the following three keys:


| Key  | Type      | Meaning             |
| ---- | --------- | ------------------- |
| cmst | Container | dmcp.playstatus     |
| mstt | uint32    | dmap.status         |
| cmsr | uint32    | dmcp.serverrevision |

Now, let us try to decode the following binary data with the table above:

    636d7374000000186d73747400000004000000c8636d73720000000400000019

We know that key and length fields are always four bytes, so lets split the
TLV so we more easily can see what is happening:

    636d7374 00000018 6d73747400000004000000c8636d73720000000400000019

How nice,  0x636d7374 corresponds to *cmst* in ASCII and we happen to know
what that is. We can also see that the data is 0x18 = 24 bytes long which so
happens to be the remaining data. All the following TLVs are thus children
to *cmst* since that is a container. Lets continue and split the remaining
data:

    6d737474 00000004 000000c8636d73720000000400000019

Again, we can see that the key 0x6d737474 is *mstt* in ASCII. This is a uint32
which means that the size is four bytes and the we should interpret the four
following bytes a uint32:

    000000c8 = 200

Since we have data remaining, that should be another TLV and we have to
continue decoding that one as well. Same procedure:

    636d7372 00000004 00000019

The tag is 0x636d7372 = *cmsr*, size is four bytes (uint32) and the decoded
value is 25. The final decoding looks like this:

    + cmst:
      |
      +- mstt: 200
      |
      +- cmsr: 25

Note that *mstt* and *cmsr* are part of the *cmst* container. This is a typical
response that the Apple TV responds with when doing a "playstatusupdate" request
and nothing is currently playing. Other keys and values are included when
you for instance are playing video or music.

## Request URLs

Since DAAP is sent over HTTP, requests can be made with any HTTP client. However,
some special headers must be included. These have been extracted with Wireshark
when using the Remote app on an iPhone and covers `GET`-requests:

| Header                        | Value                                        |
| ----------------------------- | -------------------------------------------- |
| Accept                        | */*                                          |
| Accept-Encoding               | gzip                                         |
| Client-DAAP-Version           | 3.13                                         |
| Client-ATV-Sharing-Version    | 1.2                                          |
| Client-iTunes-Sharing-Version | 3.15                                         |
| User-Agent                    | Remote/1021                                  |
| Viewer-Only-Client            | 1                                            |

For `POST`-request, the following header must be present as well:

| Header       | Value                             |
| ------------ | --------------------------------- |
| Content-Type | application/x-www-form-urlencoded |

There are a lot of different requests that can be sent and this library
implements far from all of them. Fact is that there is support for things that
aren't implemented by the native Remote app, like scrubbing (changing absolute
position in the stream). Since it's the same commands as used by iTunes, we can
probably assume that it's the same software implementation used in both
products. Enough on that matter... All the requests that are used by this
library is described in its own chapter a bit further down.

## Authentication

Some commands can be queried freely by anyone on the same network as the Apple TV,
like the server-info command. But most commands require a "session id". The
session id is obtained by doing login and extracting the `mlid` key. Session id
is then included in all requests, e.g.

    ctrl-int/1/playstatusupdate?session-id=<session id>&revision-number=0

The device will respond with an error (503?) if the authentication fails.

## Supported Requests

This list is only covers the requests performed by `pyatv` and is thus not
complete.

### server-info

**Type:** GET

**URL:** server-info

**Authentication:** None

Returns various information about a device. Here is an example:

    msrv: [container, dmap.serverinforesponse]
      mstt: 200 [uint, dmap.status]
      mpro: 131082 [uint, dmap.protocolversion]
      minm: Apple TV [str, dmap.itemname]
      apro: 196620 [uint, daap.protocolversion]
      aeSV: 196618 [uint, com.apple.itunes.music-sharing-version]
      mstm: 1800 [uint, dmap.timeoutinterval]
      msdc: 1 [uint, dmap.databasescount]
      aeFP: 2 [uint, com.apple.itunes.req-fplay]
      aeFR: 100 [uint, unknown tag]
      mslr: True [bool, dmap.loginrequired]
      msal: True [bool, dmap.supportsautologout]
      mstc: 1485803565 [uint, dmap.utctime]
      msto: 3600 [uint, dmap.utcoffset]
      atSV: 65541 [uint, unknown tag]
      ated: True [bool, daap.supportsextradata]
      asgr: 3 [uint, com.apple.itunes.gapless-resy]
      asse: 7341056 [uint, unknown tag]
      aeSX: 3 [uint, unknown tag]
      msed: True [bool, dmap.supportsedit]
      msup: True [bool, dmap.supportsupdate]
      mspi: True [bool, dmap.supportspersistentids]
      msex: True [bool, dmap.supportsextensions]
      msbr: True [bool, dmap.supportsbrowse]
      msqy: True [bool, dmap.supportsquery]
      msix: True [bool, dmap.supportsindex]
      mscu: 101 [uint, unknown tag]

### login

**Type:** GET

**URL:** login?hsgid=<hsgid>&hasFP=1

**URL:** login?pairing-guid=<PAIRING GUID>&hasFP=1

**Authentication:** HSGID or PAIRING GUID

Used to login and get a `session id`, that is needed for most commands.
Example response from device:

    mlog: [container, dmap.loginresponse]
      mstt: 200 [uint, dmap.status]
      mlid: 1739004399 [uint, dmap.sessionid]

Expected format for HSGID and PAIRING GUID respectively:

* HSGID: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`
* PAIRING GUID: `0xXXXXXXXXXXXXXXXX`

Where `X` corresponds to a hex digit (0-F).

### playstatusupdate

**Type:** GET

**URL:** ctrl-int/1/playstatusupdate?session-id=<session id>&revision-number=<revision number>

**Authentication:** Session ID

The response contains information about what is currently playing. Example
response:

    cmst: [container, dmcp.playstatus]
      mstt: 200 [uint, dmap.status]
      cmsr: 159 [uint, dmcp.serverrevision]
      caps: 4 [uint, dacp.playstatus]
      cash: 0 [uint, dacp.shufflestate]
      carp: 0 [uint, dacp.repeatstate]
      cafs: 0 [uint, dacp.fullscreen]
      cavs: 0 [uint, dacp.visualizer]
      cavc: False [bool, dacp.volumecontrollable]
      caas: 1 [uint, dacp.albumshuffle]
      caar: 1 [uint, dacp.albumrepeat]
      cafe: False [bool, dacp.fullscreenenabled]
      cave: False [bool, dacp.dacpvisualizerenabled]
      ceQA: 0 [uint, unknown tag]
      cann: Call On Me - Ryan Riback Remix [str, daap.nowplayingtrack]
      cana: Starley [str, daap.nowplayingartist]
      canl: Call On Me (Remixes) [str, daap.nowplayingalbum]
      ceSD: b'...' [raw, unknown tag]
      casc: 1 [uint, unknown tag]
      caks: 6 [uint, unknown tag]
      cant: 214005 [uint, dacp.remainingtime]
      cast: 222000 [uint, dacp.tracklength]
      casu: 0 [uint, dacp.su]

The field `cmsr` (dmcp.serverrevision) is used to realize "push updates".
By setting `<revision number>` to this number, the GET-request will block
until something happens on the device. This number will increase for each
update, so the next time it will be 160, 161, and so on. Using revision
number 0 will never block and can be used to poll current playstatus.

### nowplayingartwork

**Type:** GET

**URL:** ctrl-int/1/nowplayingartwork?mw=1024&mh=576&session-id=<session id>

**Authentication:** Session ID

Returns a PNG image for what is currently playing, like a poster or album art.
If not present, an empty response is returned. Width and height of image can be
altered with `mw` and `mh`, but will be ignored if available image is smaller
then the requested size.

### ctrl-int

**Type:** POST

**URL:** ctrl-int/1/<command>?session-id=<session id>&prompt-id=0

**Authentication:** Session ID

<command> corresponds to the command to execute. Can be any of `play`, `pause`,
`nextitem` or `previtem`.

### controlpromptentry

**Type:** POST

**URL:** ctrl-int/1/controlpromptentry?session-id=<session id>&prompt-id=0

**Authentication:** Session ID

Used to trigger various buttons, like menu or select. Must contain the
following binary DMAP data:

    cmbe: <command> [string]
    cmcc: 0 [string]

No external container is used. <command> can be either `select`, `menu` or
`topmenu`.

### setproperty

**Type:** POST:

**URL:** ctrl-int/1/setproperty?<key>=<value>&session-id=<session id>&prompt-id=0

**Authentication:** Session ID

Changes a property for something.

Summary of supported properties:

| Key                   | Type | Value                               |
| --------------------- | ---- | ----------------------------------- |
| dacp.playingtime      | uint | Time in seconds                     |
| dacp.shufflestate     | bool | Shuffle state on/off                |
| dacp.repeatstate      | uint | Repeat mode (0=Off, 1=Track, 2=All) |


## References

Https://en.wikipedia.org/wiki/Digital_Media_Access_Protocol

https://github.com/benumc/Apple-TV-Basic-IP/blob/master/apple_apple%20tv%20(ip).xml

https://nto.github.io/AirPlay.html

http://stackoverflow.com/questions/35355807/has-anyone-reversed-engineered-the-protocol-used-by-apples-ios-remote-app-for-c

# Media Remote Protocol (MRP)

The Media Remote Protocol (MRP) was introduced somewhere along the line of when Apple TV 4
and tvOS was launched. It is the protocol used by the Remote App as well as the Control
Center widget in iOS. It is also the reason why devices not running tvOS (e.g. Apple TV 3)
cannot be controlled from Control Center.

From a protocol point-of-view, it is based on Protocol Buffers
[(protobuf)](https://developers.google.com/protocol-buffers), developed by Google.
Every message is prefixed with a variant (in protobuf terminology), since protobuf
messages doesn't have lengths themselves. Service discovery is done with Zeroconf
using service `_mediaremotetv._tcp.local.`. The service contains some basic information,
like device name, but also which port that is used for communication. The port can
change at any time (e.g. after reboot, but also at more random times) and usually
start with 49152 - the first ephemeral port.

## Implementation

This is currently TBD, but you can can the code under `pyatv/mrp`.

## References

In order to not duplicate information, please read more about the protocol
[here](https://github.com/jeanregisser/mediaremotetv-protocol).

# Companion Link

The Companion Link protocol is yet another protocol used to communicate between Apple
devices. Its full purpose is not yet fully understood, so what is written here are
mostly speculations and guesses. If you feel that something wrong or have more details,
please let me know.

Main driver for reverse engineering this protocol was to be able to launch apps in the
same way as the Shortcuts app, which was introduced in iOS 13. In iOS 13 Apple also
decided to switch from MRP to Companion Link in the remote widget found in action center.
Adding server-side support for Companion Link to the proxy would be a nice feature.
Guesses are that Continuity and Handoff are also built on top of this protocol, but that
is so far just speculations.

## Service Discovery

Like with  most Apple services, Zeroconf is used for service discovery. More precisely,
`_companion-link._tcp.local.` is the used service type. Here's a list of the properties
included in this service and typical values:

| Property | Example Value | Meaning |
| -------- | ------------- | ------- |
| rpHA | 45efecc5211 | Something related to HomeKit?
| rpHN | 86d44e4f11ff | Discovery Nounce
| rpVr | 195.2 | Likely protocol version
| rpMd | AppleTV6,2 | Device model name
| rpFl | 0x36782 | Some status flags (or supported features)
| rpAD | cc5011ae31ee | Bonjour Auth Tag
| rpHI | ffb855e34e31 | Something else related to HomeKit
| rpBA | E1:B2:E3:BB:11:FF | Bluetooth Address

Most values (except for rpVr, rpMd and rpFl) change every time the Apple TV is rebooted. It is
assumed to be for privacy reasons. It is still not known how these values are to be used.

## Binary Format

The binary format is quite simple as it only consists of a message type, payload length
and the actual payload:

| Frame Type (1 byte) | Length (3 bytes) | Payload |

Since the message type is called "frame type", one message will be referred to as a
frame. The following frame types are currently known:

| Id   | Name | Note |
| ---- | ---- | ---- |
| 0x00 | Unknown |
| 0x01 | NoOp |
| 0x03 | PS\_Start | Pair-Setup initial measage
| 0x04 | PS\_Next | Pair-Setup following messages
| 0x05 | PV\_Start | Pair-Verify initial message
| 0x06 | PV\_Next | Pair-Verify following measages
| 0x07 | U_OPACK |
| 0x08 | E_OPACK | This is used when launching apps
| 0x09 | P_OPACK |
| 0x0A | PA\_Req |
| 0x0B | PA\_Rsp |
| 0x10 | SessionStartRequest |
| 0x11 | SessionStartResponse |
| 0x12 | SessionData |
| 0x20 | FamilyIdentityRequest |
| 0x21 | FamilyIdentityResponse |
| 0x22 | FamilyIdentityUpdate |

The length field determines the size of the following payload in bytes (stored as
big endian). So far only responses with frame type `E_OPACK` has been seen. The payload
in these frames are encoded with OPACK (described below), which should also be these
case for `U_OPACK` and `P_OPACK`.

## OPACK

OPACK is an Apple internal serialization format found in the CoreUtils private framework.
It can serialize basic data types, like integers, strings, lists and dictionaries
in an efficient way. In some instances (like booleans and small numbers), a single
byte is sufficient. In other cases dynamic length fields are used to encode data size.

Most parts of this format has been reverse engineered, but it's not complete or
verified to be correct. If any discrepancies are found, please report them.

An object is encoded or decoded according to this table:

| Bytes | Kind of Data | Example (python-esque) |
| ----- | ------------ | ---------------------- |
| 0x01 | true | 0x01 = True
| 0x02 | false | 0x02 = False
| 0x04 | null | 0x04 = None
| 0x06 | absolute time | 0x062471BB36 = 2020-05-17 18:34:30
| 0x08-0x2F | 0-39 (decimal) | 0x17 = 15 (decimal)
| 0x30 | int32 1 byte length | 0x300120 = 32 (decimal)
| 0x31 | int32 2 byte length | 0x31010020 = 32 (decimal)
| 0x32 | int32 3 byte length | 0x3201000020 = 32 (decimal)
| 0x33 | int32 4 byte length | 0x330100000020 = 32 (decimal)
| 0x35 | float32 | 0x35xxxxxxxx = xxxxxxxx (signed, single precision)
| 0x36 | float64 | 0x36xxxxxxxxxxxxxxxx = xxxxxxxxxxxxxxxx (signed, double precision)
| 0x40-0x60 | string (0-32 chars) | 0x43666F6F = "foo"
| 0x61 | string 1 byte length | 0x6103666F6F = "foo"
| 0x62 | string 2 byte length | 0x620300666F6F = "foo"
| 0x63 | string 3 byte length | 0x62030000666F6F = "foo"
| 0x64 | string 4 byte length | 0x6303000000666F6F = "foo"
| 0x70-0x90 | raw bytes (0-32 bytes) | 0x72AABB = b"\xAA\xBB"
| 0x91 | data 1 byte length | 0x9102AABB = b"\xAA\xBB"
| 0x92 | data 2 byte length | 0x920200AABB = b"\xAA\xBB"
| 0x93 | data 3 byte length | 0x93020000AABB = b"\xAA\xBB"
| 0x94 | data 4 byte length | 0x9402000000AABB = b"\xAA\xBB"
| 0xDv | array with *v* elements | 0xD2016103666F6F = [True, "foo"]
| 0xEv | dictionary with *v* entries | 0xE16103666F6F0x17 = {"foo": 15}

## Authentication

Devices are paired and data encrypted according to HAP (HomeKit). More or less... This
part has not yet been fully figured out and will be updated along the way.

Messages will be presented both in hex but also a decoded format, based on the
implementation in `pyatv`. So beware that it will be somewhat python-inspired.

## Pairing

To start pairing, a frame with frame type `PA_Start` is sent:

```
Hex:
03000013e2435f706476000100060101
455f7077547909

Decoded:
Frame(type=<FrameType.PS_Start: 3>, data={'_pd': {'0': b'\x00', '6': b'\x01'}, '_pwTy': 1})
```
The paylod contains the following:

| Field | Value |
| ----- | ----- |
| *\_pd* | TLV8 with method (0x00) set to None (0x00) and state (0x06) set to M1 (0x01).
| *\_pwTy* | Set to 1, corresponding to PIN code.

The device will respond like this:

```
Hex:
040001a4e1435f7064929c0106010202
10dff7fb13e786a565f292ead111f6c0
1d03ffd734f8fac8235e3cfa1c7b893f
63ef7936205c0ff7cd47b7281e403b29
7f70deb063a1baa1d35ce5a54e6a6f7b
3376d5d749e719caa2625371c2bbc611
f49637eae1990fa16c5a9c77b3072495
2b77fb0d0e7f5c3dd2fc90e495a82975
2aba0657f053a9bdff6a46cc51ed67e3
4a05ae1f563e6dcc66e292532a71f20d
57c98ca1a190773db6aed5fac3bd30a6
9426c33f0a931d090ad331d4fb5b0442
8e3b471eaa6119a13af1e559529e7565
2efa1bf283942ffe5b6037c72542daae
284ffa6fca413d329d76c7ce788a67fa
6631e25c7d913d3b19156ad631900d52
4f4dee6fac8fe4aaf64927de319dee30
0b733f8225a856ffba7ef32863123320
e1ef0381c39cf11a52c5f2b56a28b936
bd1a8fc6e8fdeda88431545733084807
1387c9099e073ba412b5ab91ebcfe52f
5503d6943219192519ad131848eb61ff
c3a95e8175456eeba1f3aa9b6cf5514f
b0a7b697bc950c47c533797982728c95
00b5bb5a43e13b13fa458b28050e3536
482905773f935e10535c9ac25ed0f120
aaf54645001b0101

Decoded:
Frame(type=<FrameType.PS_Next: 4>, data={'_pd': {'6': b'\x02', '2': b'\xdf\xf7\xfb\x13\xe7\x86\xa5e\xf2\x92\xea\xd1\x11\xf6\xc0\x1d', '3': b"\xd74\xf8\xfa\xc8#^<\xfa\x1c{\x89?c\xefy6 \\\x0f\xf7\xcdG\xb7(\x1e@;)\x7fp\xde\xb0c\xa1\xba\xa1\xd3\\\xe5\xa5Njo{3v\xd5\xd7I\xe7\x19\xca\xa2bSq\xc2\xbb\xc6\x11\xf4\x967\xea\xe1\x99\x0f\xa1lZ\x9cw\xb3\x07$\x95+w\xfb\r\x0e\x7f\\=\xd2\xfc\x90\xe4\x95\xa8)u*\xba\x06W\xf0S\xa9\xbd\xffjF\xccQ\xedg\xe3J\x05\xae\x1fV>m\xccf\xe2\x92S*q\xf2\rW\xc9\x8c\xa1\xa1\x90w=\xb6\xae\xd5\xfa\xc3\xbd0\xa6\x94&\xc3?\n\x93\x1d\t\n\xd31\xd4\xfb[\x04B\x8e;G\x1e\xaaa\x19\xa1:\xf1\xe5YR\x9eue.\xfa\x1b\xf2\x83\x94/\xfe[`7\xc7%B\xda\xae(O\xfao\xcaA=2\x9dv\xc7\xcex\x8ag\xfaf1\xe2\\}\x91=;\x19\x15j\xd61\x90\rROM\xeeo\xac\x8f\xe4\xaa\xf6I'\xde1\x9d\xee0\x0bs?\x82%\xa8V\xff\xba~\xf3(c\x123 \xe1\xef\xc3\x9c\xf1\x1aR\xc5\xf2\xb5j(\xb96\xbd\x1a\x8f\xc6\xe8\xfd\xed\xa8\x841TW3\x08H\x07\x13\x87\xc9\t\x9e\x07;\xa4\x12\xb5\xab\x91\xeb\xcf\xe5/U\x03\xd6\x942\x19\x19%\x19\xad\x13\x18H\xeba\xff\xc3\xa9^\x81uEn\xeb\xa1\xf3\xaa\x9bl\xf5QO\xb0\xa7\xb6\x97\xbc\x95\x0cG\xc53yy\x82r\x8c\x95\x00\xb5\xbbZC\xe1;\x13\xfaE\x8b(\x05\x0e56H)\x05w?\x93^\x10S\\\x9a\xc2^\xd0\xf1 \xaa\xf5FE\x00", '27': b'\x01'}})
```

| Field | Value |
| ----- | ----- |
| *\_pd* | TLV8 with state (0x06) set to M2 (0x02), salt (0x02) set to a 16 byte value and public key (0x03) set to a 384 byte value. The tag 0x1B is not yet known.

At this stage a PIN code is displayed on the screen. Rest is TBD.

## Verification

TBD

# AirPlay

Currently, `pyatv` only supports playing a video (or audio) by providing a URL.
Since tvOS 10.2, device authentication ("pairing") was enforced and that process
is supported since a while back.

More information will be added here later

## References

[Unofficial AirPlay Protocol Specification](https://nto.github.io/AirPlay.html)