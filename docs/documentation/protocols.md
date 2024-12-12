---
layout: template
title: Protocols
permalink: /documentation/protocols/
link_group: documentation
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}


# Protocols

If you want to extend pyatv, a basic understanding of the used protocols helps a lot. This
page aims to give a summary of the protocols and how they work (to the extent we know, since
they are reverse engineered). Focus are on the parts that are relevant and implemented in
pyatv.

# Digital Media Access Protocol (DMAP)

DMAP covers the suite of protocols used by various Apple software (e.g. iTunes)
to share, for instance, music. There are already a bunch of sites and libraries describing
and implementing these protocols. Please see the reference further down. This section will
focus on the technical aspects used to implement DMAP/DACP/DAAP in pyatv.

At its core, DMAP is basically a HTTP server (running on port 3689) that responds to specific
commands and streams events back to the client. Data is requested using GET and POST methods with
special URLs. Data in the responses is usually in a specific binary format, whose format can depend on
the request (like a PNG file for artwork). The
binary protocol will be explained first, as that makes it easier to understand
the requests.

## DMAP Binary Format

The binary format is basically [type-length-value](https://en.wikipedia.org/wiki/Type–length–value)
(TLV) data where the tag (or key) is a 4 byte ASCII-string,
the length is a four byte unsigned integer and the data is, well, data. Type
and meaning of a specific TLV are derived from the tag. So one must know which
tags are used, how large they are and what they mean. Please note that Length
is length of the data, so key and length are not included in this size.

A TLV looks like this:

| Key (4 bytes) | Length (4 bytes) | Data (Length) bytes |

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
since multiple TLVs with the same key often occur.

All tags currently known by pyatv are defined in `pyatv.dmap.tag_definitions`.

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
implements far from all of them. There is actually support for things that
aren't implemented by the native Remote app, like scrubbing (changing absolute
position in the stream). Since it's the same commands as used by iTunes, we can
probably assume that it's the same software implementation used in both
products. Enough on that matter... All the requests that are used by this
library is described in their own chapter a bit further down.

## Authentication

Some commands can be queried freely by anyone on the same network as the Apple TV,
like the server-info command. But most commands require a "session id". The
session id is obtained by doing a login and extracting the `mlid` key. Session id
is then included in all requests, e.g.

    ctrl-int/1/playstatusupdate?session-id=<session id>&revision-number=0

The device will respond with an error (503?) if the authentication fails.

## Supported Requests

This list only covers the requests performed by pyatv and is incomplete.

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
altered with `mw` and `mh`, but will be ignored if the available image is smaller
than the requested size.

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

The Media Remote Protocol (MRP) was introduced some time when Apple TV 4
and tvOS was launched. It is the protocol used by the Remote App as well as the Control
Center widget in iOS before iOS13. It is also the reason devices not running tvOS (e.g. Apple TV 3)
cannot be controlled from Control Center.

From a protocol point-of-view, it is based on Protocol Buffers
[(protobuf)](https://developers.google.com/protocol-buffers), developed by Google.
Every message is prefixed with a variant (in protobuf terminology), since protobuf
messages don't have lengths themselves. Service discovery is done with Zeroconf
using service `_mediaremotetv._tcp.local.`. The service contains some basic information,
like device name, but also which port is used for communication. The port can
change at any time (e.g. after reboot, but also at more random times) and usually
start with 49152 - the first ephemeral port.

## Implementation

This is currently TBD, but you can can the code under `pyatv/mrp`.

## References

In order not to duplicate information, please read more about the protocol
[here](https://github.com/jeanregisser/mediaremotetv-protocol).

# Companion Link

The Companion Link protocol is yet another protocol used to communicate between Apple
devices. Its purpose is not yet fully understood, so what is written here is
mostly speculation and guesses. If you feel that something is wrong or have more details,
please let me know.

The main driver for reverse engineering this protocol was to be able to launch apps in the
same way as the Shortcuts app, which was introduced in iOS 13. In iOS 13 Apple also
decided to switch from MRP to Companion Link in the remote widget found in action center.
Adding server-side support for Companion Link to the proxy would be a nice feature.
Guesses are that Continuity and Handoff are also built on top of this protocol, but that
is so far just speculation.

## Service Discovery

Like with most Apple services, Zeroconf is used for service discovery. More precisely,
`_companion-link._tcp.local.` is the used service type. Here's a list of the properties
included in this service and typical values:

| Property | Example Value | Meaning |
| -------- | ------------- | ------- |
| rpHA | 45efecc5211 | HomeKit AuthTag
| rpHN | 86d44e4f11ff | Discovery Nonce
| rpVr | 195.2 | Likely protocol version
| rpMd | AppleTV6,2 | Device model name
| rpFl | 0x36782 | Some status flags (or supported features)
| rpAD | cc5011ae31ee | Bonjour Auth Tag
| rpHI | ffb855e34e31 | HomeKit rotating ID
| rpBA | E1:B2:E3:BB:11:FF | Bluetooth Address (can rotate)

Most values (except for rpVr, rpMd and rpFl) change every now and then (rotating encryption
scheme), likely for privacy reasons. It is still not known how these values are consumed.

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
big endian). So far, only responses with frame type `E_OPACK` has been seen. The payload
in these frames is encoded with OPACK (described below), which should also be the
case for `U_OPACK` and `P_OPACK`.

## OPACK

OPACK is an Apple internal serialization format found in the CoreUtils private framework.
It can serialize basic data types, like integers, strings, lists and dictionaries
in an efficient way. In some instances (like booleans and small numbers), a single
byte is sufficient. In other cases dynamic length fields are used to encode data size. Data is encoded using little endian where applicable and unless stated otherwise.

Most parts of this format have been reverse engineered, but it's not complete or
verified to be correct. If any discrepancies are found, please report them or open a PR.

An object is encoded or decoded according to this table:

| Bytes | Kind of Data | Example (python-esque) |
| ----- | ------------ | ---------------------- |
| 0x00 | Invalid | Reserved
| 0x01 | true | 0x01 = True
| 0x02 | false | 0x02 = False
| 0x03 | termination | 0xEF4163416403 = {"a": "b"} (See [Endless Collections](#endless-collections))
| 0x04 | null | 0x04 = None
| 0x05 | UUID4 (16 bytes) big-endian | 0x0512345678123456781234567812345678 = 12345678-1234-5678-1234-567812345678
| 0x06 | absolute mach time little-endian | 0x0000000000000000 = ?
| 0x07 | -1 (decimal) | 0x07 = -1 (decimal)
| 0x08-0x2F | 0-39 (decimal) | 0x17 = 15 (decimal)
| 0x30 | int32 1 byte length | 0x3020 = 32 (decimal)
| 0x31 | int32 2 byte length | 0x310020 = 32 (decimal)
| 0x32 | int32 4 byte length | 0x3200000020 = 32 (decimal)
| 0x33 | int32 8 byte length | 0x330000000000000020 = 32 (decimal)
| 0x34 | int32 16 byte length | 
| 0x35 | float32 | 0x35xxxxxxxx = xxxxxxxx (signed, single precision)
| 0x36 | float64 | 0x36xxxxxxxxxxxxxxxx = xxxxxxxxxxxxxxxx (signed, double precision)
| 0x40-0x60 | string (0-32 chars) | 0x43666F6F = "foo"
| 0x61 | string 1 byte length | 0x6103666F6F = "foo"
| 0x62 | string 2 byte length | 0x620300666F6F = "foo"
| 0x63 | string 3 byte length | 0x62030000666F6F = "foo"
| 0x64 | string 4 byte length | 0x6303000000666F6F = "foo"
| 0x6F | null terminated string | 0x6F666F6F00 = "foo"
| 0x70-0x90 | raw bytes (0-32 bytes) | 0x72AABB = b"\xAA\xBB"
| 0x91 | data 1 byte length | 0x9102AABB = b"\xAA\xBB"
| 0x92 | data 2 byte length | 0x920200AABB = b"\xAA\xBB"
| 0x93 | data 3 byte length | 0x93020000AABB = b"\xAA\xBB"
| 0x94 | data 4 byte length | 0x9402000000AABB = b"\xAA\xBB"
| 0xA0-0xC0 | pointer | 0xD443666F6F43626172A0A1 = ["foo", "bar", "foo", "bar"] (see [Pointers](#pointers))
| 0xC1 | pointer 1 bytes length | 0xC102 = 2 (see [Pointers](#pointers))
| 0xC2 | pointer 2 bytes length | 0xC20002 = 2 (see [Pointers](#pointers))
| 0xC2 | pointer 3 bytes length | 0xC3000002 = 2 (see [Pointers](#pointers))
| 0xC4 | pointer 4 bytes length | 0xC400000003 = 2 (see [Pointers](#pointers))
| 0xDv | array with *v* elements | 0xD2016103666F6F = [True, "foo"]
| 0xEv | dictionary with *v* entries | 0xE16103666F6F0x17 = {"foo": 15}

### Endless Collections

Dictionaries and lists support up to 14 elements when including number of elements in a single byte, e.g. `0xE3` corresponds to a
dictionary with three elements. It is however possible to represent lists, dictionaries and data objects with an endless amount of items
using `F` as count, i.e. `0xDF`, `0xEF` or `0x9F`. A byte with value `0x03` indicates end of a list, dictionary or data object.

A simple example with just one element, e.g. ["a"] looks like this:

```raw
0xDF416103
```

Decoded form:

```raw
DF    : Endless list
41 61 : "a"
03    : Terminates previous list (or dict)
```

### Pointers

To save space, a *pointer* can be used to refer to an already defined object. A pointer is an index referring to the object order in the
byte stream, i.e. if three strings are placed in a list, index 0 would refer to the first string, index 1 to the second and so on. Lists and
dictionary bytes are ignored as well as other types represented by a single byte (e.g. a bool) as no space would be saved by a pointer.

The index table can be constructed by appending every new decoded object (excluding ignored types) to list. When a pointer byte is found,
subtract `0xA0` and use the obtained value as index in the list.

Here is a simple example to illustrate:

```yaml
{
  "a": False,
  "b": "test",
  "c": "test
}
```

The above data structure would serialize to:

```raw
E3416102416244746573744163A2
```

Break-down of the data:

```raw
E3          : Dictionary with three items
41 61       : "a"
02          : False
41 62       : "b"
44 74657374 : "test"
41 63       : "c"
A2          : Pointer, index=2

```

As single byte objects are ignored, the constructed index list looks
like `[a, b, test, c]`. Index 2 translates to `"test"` and  `0xA2` is simply
replaced by that value.

The range `0xA0-0xC0` can be used to reference an object using a single byte.
It is also possible to use `0xC1-0xC4` to address objects beyond that. The lower
nibble (1-4) indicates how many bytes are used for the index.

### Reference Decoding
To play around with various OPACK input, this example application can be used (only on macOS):

```objectivec
#import <Foundation/Foundation.h>
#import <Foundation/NSJSONSerialization.h>

CFMutableDataRef OPACKEncoderCreateData(NSObject *obj, int32_t flags, int32_t *error);
NSObject* OPACKDecodeBytes(const void *ptr, size_t length, int32_t flags, int32_t *error);

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSError *e = nil;
        NSFileHandle *stdInFh = [NSFileHandle fileHandleWithStandardInput];
        NSData *stdin = [stdInFh readDataToEndOfFile];

        int decode_error = 0;
        NSObject *decoded = OPACKDecodeBytes([stdin bytes], [stdin length], 0, &decode_error);
        if (decode_error) {
            NSLog(@"Failed to decode: %d", decode_error);
            return -1;
        }

        NSLog(@"Decoded: %@", decoded);
    }
    return 0;
}
```

Compile with:
```shell
xcrun clang -fobjc-arc -fmodules -mmacosx-version-min=10.6 -F /System/Library/PrivateFrameworks/ -framework CoreUtils decode.m -o decode
```

Then pass hex data to it like this:

```shell
$ echo E3416102416244746573744163A2 | xxd -r -p | ./decode
2021-04-19 21:14:57.243 decode[59438:2193666] decoded: {
    a = 0;
    b = test;
    c = test;
}
```

This excellent example comes straight from [fabianfreyer/opack-tools](https://github.com/fabianfreyer/opack-tools).

## Authentication

Devices are paired and data encrypted according to HAP (HomeKit). You can refer to that specification
for further details (available [here](https://developer.apple.com/homekit/specification/),
but it requires an Apple ID, except for the Non-Commercial version, free to download).

Messages are presented in hex and a decoded format, based on the implementation in
pyatv. So beware that it will be somewhat python-oriented.

### Pairing

The pairing sequence is initiated by the client sending a frame with type `PA_Start`. The following messages always use `PA_Next` as frame type. A typical flow looks like this (details below):

<code class="diagram">
sequenceDiagram
    autonumber
    Client->>ATV: M1: Pair-Setup Start (0x03)
    Note over Client,ATV: _pd: Method=0x00, State=M1<br/>_pwTy: 1 (PIN Code)
    ATV->>Client: M2: Pair-Setup Next (0x04)
    Note over ATV,Client: _pd: State=M2, Salt, Pubkey, 0x1B (Unknown)
    Note over Client,ATV: PIN Code is displayed on screen
    Client->>ATV: M3: Pair-Setup Next (0x04)
    Note over Client,ATV: _pd: State=M3, Pubkey, Proof<br/>_pwTy: 1 (PIN Code)
    ATV->>Client: M4: Pair-Setup Next (0x04)
    Note over ATV,Client: _pd: State=M4, Proof
    Client->>ATV: M5: Pair-Setup Next (0x04)
    Note over Client,ATV: _pd: State=M5, Encrypted Data<br/>_pwTy: 1 (PIN Code)
    ATV->>Client: M6: Pair-Setup Next (0x04)
    Note over ATV,Client: _pd: State=M6, Encrypted Data
</code>

The content of each frame is OPACK data containing a dictionary. The `_pd` key (*pairing data*) is TLV8 data according to HAP, and should be decoded according to that specification. Next follows more details for each message.

#### Client -> ATV: M1: Pair-Setup Start (0x03)
A client initiates a pairing request by sending a `PS_Start` message (M1).

Example data:
```raw
Hex:
03000013e2435f706476000100060101455f7077547909

Decoded:
frame_type=<FrameType.PS_Start: 3>, length=19, data={'_pd': {0: b'\x00', 6: b'\x01'}, '_pwTy': 1}
```

#### ATV -> Client: M2: Pair-Setup Next (0x04)
When the ATV receives a `PS_Start` (M1), it will respond with `PS_Next` (M2) containing its public key (0x03) and salt (0x02). At this stage, a PIN code is displayed on screen which the client needs to generate a proof (0x04) sent in M3.

Example data:
```raw
Hex:
040001a4e1435f7064929c0106010202102558953b4496aecea0a367bafb29e98503ff6c33b53ca685062f6b8953f303bc30a01f0edeb64ed0cffaf570cc1b3aa9de5a7482d854671a8f72a9f72e3b5cbc60631499e292b4d749d9f0f69d47de657e63517753e342fbddea38d99cd69794847487accecd07993fabc60dcda50a25850c37357f1962c7eef91042381d951d9897030e57e7b12823c24ee183cc901e41d4f2dbf9de1e673574aedfaeaa86a5c37eaeccba1e112e3f650aa69389ac73c00dd405bbf0e7b204167974cf77295a1acde14a437f58fa9555de4b00b3d88e82ee375042ae54b7473303aa5a7091cd88f5e4a1fb63c2d80005f743e2484d4a1636509356f295dab6726410670ae2b514f68300c92643960e79963223b4809e69038194fab97b932b168a7962f3db8be188a418e25506c04c50aab80c2b42dfc108cedc7c5f0a9cbe23c9d34417a7840ec321071d32ca113a0fa2c7bbe3660efe21129eb407143e89a6ff5e655ae9c95dd735cb4130aadf46943653af001a4a981d32b12bf04f06dd85788c8e8401e5f4b544a72ddf8e58193f5873d9cfcdd3415393101b0101

Decoded:
frame_type=<FrameType.PS_Next: 4>, length=420, data={'_pd': {6: b'\x02', 2: b'%X\x95;D\x96\xae\xce\xa0\xa3g\xba\xfb)\xe9\x85', 3: b'l3\xb5<\xa6\x85\x06/k\x89S\xf3\x03\xbc0\xa0\x1f\x0e\xde\xb6N\xd0\xcf\xfa\xf5p\xcc\x1b:\xa9\xdeZt\x82\xd8Tg\x1a\x8fr\xa9\xf7.;\\\xbc`c\x14\x99\xe2\x92\xb4\xd7I\xd9\xf0\xf6\x9dG\xdee~cQwS\xe3B\xfb\xdd\xea8\xd9\x9c\xd6\x97\x94\x84t\x87\xac\xce\xcd\x07\x99?\xab\xc6\r\xcd\xa5\n%\x85\x0c75\x7f\x19b\xc7\xee\xf9\x10B8\x1d\x95\x1d\x98\x97\x03\x0eW\xe7\xb1(#\xc2N\xe1\x83\xcc\x90\x1eA\xd4\xf2\xdb\xf9\xde\x1eg5t\xae\xdf\xae\xaa\x86\xa5\xc3~\xae\xcc\xba\x1e\x11.?e\n\xa6\x93\x89\xacs\xc0\r\xd4\x05\xbb\xf0\xe7\xb2\x04\x16yt\xcfw)Z\x1a\xcd\xe1JC\x7fX\xfa\x95U\xdeK\x00\xb3\xd8\x8e\x82\xee7PB\xaeT\xb7G3\x03\xaaZp\x91\xcd\x88\xf5\xe4\xa1\xfbc\xc2\xd8\x00\x05\xf7C\xe2HMJ\x166P\x93V\xf2\x95\xda\xb6rd\x10g\n\xe2\xb5\x14\xf6\x83\x00\xc9&C\x96\x0ey\x962#\xb4\x80\x9ei\x94\xfa\xb9{\x93+\x16\x8ayb\xf3\xdb\x8b\xe1\x88\xa4\x18\xe2U\x06\xc0LP\xaa\xb8\x0c+B\xdf\xc1\x08\xce\xdc|_\n\x9c\xbe#\xc9\xd3D\x17\xa7\x84\x0e\xc3!\x07\x1d2\xca\x11:\x0f\xa2\xc7\xbb\xe3f\x0e\xfe!\x12\x9e\xb4\x07\x14>\x89\xa6\xff^eZ\xe9\xc9]\xd75\xcbA0\xaa\xdfF\x946S\xaf\x00\x1aJ\x98\x1d2\xb1+\xf0O\x06\xdd\x85x\x8c\x8e\x84\x01\xe5\xf4\xb5D\xa7-\xdf\x8eX\x19?Xs\xd9\xcf\xcd\xd3AS\x93\x10', 27: b'\x01'}}
```

#### Client -> ATV: M3: Pair-Setup Next (0x04)
The client uses the PIN code to generate a proof (0x04) and sends it together with its public key in M3.

Example data:
```raw
Hex:
040001d8e2435f706492c90106010303ff992fcaa1f49bc6563e84fe283b34ba5efcf82b561dafdfcfa8dbffaa0e85fad1715b451586319cf3ec90b4961e8f793bfed6da9ab5a9b5c0fc11cb109ac91c0601801f1b150197198c44d1db67a1a0347c44db40bea50762089ea6a18896c2e161a6e80a2241e67ee8ac2cdf94c8899b09cccb310a681db44029248131dbc21ccfbdffae63d1c46e9a9ce77f309db673535dd8873100d917ee5fe13ac9a5490036cb4611ffacd0bb5389cf72aa2fbdd07227a98e83085bddd5851f459b0321a19a793ab03b5a972a0444f5a4c1e079666101b8699a9cd296d716bd87be2fcc81af4333267897ce74d4f072d8846c9d133270bae8b51bb15d0a856f06642ac903817497b588839a8ce1b4c89470cb8f5aaa647ac4387e08068c2074d42e89172bc3604a9140bba7e10404c2fecde3c02456a401c31f46ca35bf3a607e771987540607034793f42bce0685dffab35e6ff6871d9d85b3eee86d0b4069c90f024010659035a9b29adb3d6be996181eb088eb10e2706bccbc85900fca338533a891894c3c0440e4be1e32d5ba274436f38c40bc1ebbd3697b3de27e3a0908b73d7a81cdb196cdde02ed84140bae66b1149c57c62680a7d92ca503fd1a70e2d0a138800dc85324455f7077547909

Decoded:
frame_type=<FrameType.PS_Next: 4>, length=472, data={'_pd': {6: b'\x03', 3: b'\x99/\xca\xa1\xf4\x9b\xc6V>\x84\xfe(;4\xba^\xfc\xf8+V\x1d\xaf\xdf\xcf\xa8\xdb\xff\xaa\x0e\x85\xfa\xd1q[E\x15\x861\x9c\xf3\xec\x90\xb4\x96\x1e\x8fy;\xfe\xd6\xda\x9a\xb5\xa9\xb5\xc0\xfc\x11\xcb\x10\x9a\xc9\x1c\x06\x01\x80\x1f\x1b\x15\x01\x97\x19\x8cD\xd1\xdbg\xa1\xa04|D\xdb@\xbe\xa5\x07b\x08\x9e\xa6\xa1\x88\x96\xc2\xe1a\xa6\xe8\n"A\xe6~\xe8\xac,\xdf\x94\xc8\x89\x9b\t\xcc\xcb1\nh\x1d\xb4@)$\x811\xdb\xc2\x1c\xcf\xbd\xff\xaec\xd1\xc4n\x9a\x9c\xe7\x7f0\x9d\xb6sS]\xd8\x871\x00\xd9\x17\xee_\xe1:\xc9\xa5I\x006\xcbF\x11\xff\xac\xd0\xbbS\x89\xcfr\xaa/\xbd\xd0r\'\xa9\x8e\x83\x08[\xdd\xd5\x85\x1fE\x9b\x03!\xa1\x9ay:\xb0;Z\x97*\x04D\xf5\xa4\xc1\xe0yfa\x01\xb8i\x9a\x9c\xd2\x96\xd7\x16\xbd\x87\xbe/\xcc\x81\xafC3&x\x97\xcet\xd4\xf0r\xd8\x84l\x9d\x132p\xba\xe8\xb5\x1b\xb1]\n\x85o\x06d*\xc9t\x97\xb5\x88\x83\x9a\x8c\xe1\xb4\xc8\x94p\xcb\x8fZ\xaadz\xc48~\x08\x06\x8c t\xd4.\x89\x17+\xc3`J\x91@\xbb\xa7\xe1\x04\x04\xc2\xfe\xcd\xe3\xc0$V\xa4\x01\xc3\x1fF\xca5\xbf:`~w\x19\x87T\x06\x07\x03G\x93\xf4+\xce\x06\x85\xdf\xfa\xb3^o\xf6\x87\x1d\x9d\x85\xb3\xee\xe8m\x0b@i\xc9\x0f\x02@\x10e\x905\xa9\xb2\x9a\xdb=k\xe9\x96\x18\x1e\xb0\x88\xeb\x10\xe2pk\xcc\xbc\x85\x90\x0f\xca3\x853\xa8\x91\x89L<', 4: b"\xe4\xbe\x1e2\xd5\xba'D6\xf3\x8c@\xbc\x1e\xbb\xd3i{=\xe2~:\t\x08\xb7=z\x81\xcd\xb1\x96\xcd\xde\x02\xed\x84\x14\x0b\xaef\xb1\x14\x9cW\xc6&\x80\xa7\xd9,\xa5\x03\xfd\x1ap\xe2\xd0\xa18\x80\r\xc8S$"}, '_pwTy': 1}
```

#### ATV -> Client: M4: Pair-Setup Next (0x04)
The ATV also generates a proof (0x04) and sends it back to the client in M4.

Example data:
```raw
Hex:
0400004ce1435f7064914506010404402598bf58f5e3f944b63df0c1e389f59b2dff2a97e2e25d86013a1a9e18c2c69ec1960d9ca2020c1a22b656d2fbb96d390df65604f94bef0ba8cc37bbcc2eca11

Decoded:
frame_type=<FrameType.PS_Next: 4>, length=76, data={'_pd': {6: b'\x04', 4: b'%\x98\xbfX\xf5\xe3\xf9D\xb6=\xf0\xc1\xe3\x89\xf5\x9b-\xff*\x97\xe2\xe2]\x86\x01:\x1a\x9e\x18\xc2\xc6\x9e\xc1\x96\r\x9c\xa2\x02\x0c\x1a"\xb6V\xd2\xfb\xb9m9\r\xf6V\x04\xf9K\xef\x0b\xa8\xcc7\xbb\xcc.\xca\x11'}}
```

#### Client -> ATV: M5: Pair-Setup Next (0x04)
At this stage, both devices should have proved themselves to one another. The client will
create a certain payload and encrypt it with a session key and send it in M5 to the ATV.

The content of encrypted data is TLV8 encoded and contains an identifier (0x01), the clients
public key (0x03) and a signature (0x0A) according to HAP. It also contains an additional
item with data specific to the Companion protocol. It uses tag 17 and the content is encoded
with OPACK. An example of the payload looks like this (illustrative values):

```python
{
  "altIRK": b"-\x54\xe0\x7a\x88*en\x11\xab\x82v-'%\xc5",
  "accountID": "DC6A7CB6-CA1A-4BF4-880D-A61B717814DB",
  "model": "iPhone10,6",
  "wifiMAC": b"@\xff\xa1\x8f\xa1\xb9",
  "name": "Pierres iPhone",
  "mac": b"@\xc4\xff\x8f\xb1\x99"
}
```

Example data:
```
Hex:
040000ade2435f7064919f060105059af10dc2be3a537a73d7a89dd5d6a3114a6c9adbaf46a2b3a389b33381cf470de62d837f44da190266cfd4eb5c8f42350e2d4dec03e9354384be770e8f17fbf726cb21049589b912fdb88ba416dde56e033fd077e64c272f5cca2fd4c42d9143a9811f8897a81f5847fdc14f78e1bfba06005d3dc243e0ecb5af734348d7099ec1b252c64a04e04f1d146a90ad49da95f6a38e6d2755b41bc2d1b6455f7077547909

Decoded:
frame_type=<FrameType.PS_Next: 4>, length=2782, data={'_pd': {6: b'\x05', 5: b"\xf1\r\xc2\xbe:Szs\xd7\xa8\x9d\xd5\xd6\xa3\x11Jl\x9a\xdb\xafF\xa2\xb3\xa3\x89\xb33\x81\xcfG\r\xe6-\x83\x7fD\xda\x19\x02f\xcf\xd4\xeb\\\x8fB5\x0e-M\xec\x03\xe95C\x84\xbew\x0e\x8f\x17\xfb\xf7&\xcb!\x04\x95\x89\xb9\x12\xfd\xb8\x8b\xa4\x16\xdd\xe5n\x03?\xd0w\xe6L'/\\\xca/\xd4\xc4-\x91C\xa9\x81\x1f\x88\x97\xa8\x1fXG\xfd\xc1Ox\xe1\xbf\xba\x06\x00]=\xc2C\xe0\xec\xb5\xafsCH\xd7\t\x9e\xc1\xb2R\xc6J\x04\xe0O\x1d\x14j\x90\xadI\xda\x95\xf6\xa3\x8em'U\xb4\x1b\xc2\xd1\xb6"}, '_pwTy': 1}
```

#### ATV -> Client: M6: Pair-Setup Next (0x04)
The concept here is the same as M5 (same kind of encrypted data).

Example data:
```raw
Hex:
0400012fe1435f706492270105ff8efc56bf0641a0fa53f00ae8da07a4ec5e929f5ec697e8692c8e833f175ecae4e381a8ced11097c76152031374926558cc8e64a0330097a241e76580c69d5d5a5017da1c393cee663be525ac1cc47229e491b3c1834a0d32ffc121d78e2d65bbc0efb5858615f49d6d43457a7c827f5c15bfc8a9da1f75839d24dbc8ddbbf2b658d3ded2848d9e1b92e8a7f4dd09f7f81b2108cf85be3910bfbb2045043d3cf3aa9619b63ba923acdae14e3cbc5a9b16c83b9a4e33e3d88d1af6c4154973ffaa8ca08a48f964056413a62551ff4628329c3bc836dfc14873b597f223ff4c4b6e17cc062cd66b34c475b3e272ecf47a8866457eb462fb2116f9134d443369540521dcaaed3b1a4622fec7806be71d4739a8f46327e8f41cc148f23a437dafb56575c3060106

Decoded:
frame_type=<FrameType.PS_Next: 4>, length=303, data={'_pd': {5: b'\x8e\xfcV\xbf\x06A\xa0\xfaS\xf0\n\xe8\xda\x07\xa4\xec^\x92\x9f^\xc6\x97\xe8i,\x8e\x83?\x17^\xca\xe4\xe3\x81\xa8\xce\xd1\x10\x97\xc7aR\x03\x13t\x92eX\xcc\x8ed\xa03\x00\x97\xa2A\xe7e\x80\xc6\x9d]ZP\x17\xda\x1c9<\xeef;\xe5%\xac\x1c\xc4r)\xe4\x91\xb3\xc1\x83J\r2\xff\xc1!\xd7\x8e-e\xbb\xc0\xef\xb5\x85\x86\x15\xf4\x9dmCEz|\x82\x7f\\\x15\xbf\xc8\xa9\xda\x1fu\x83\x9d$\xdb\xc8\xdd\xbb\xf2\xb6X\xd3\xde\xd2\x84\x8d\x9e\x1b\x92\xe8\xa7\xf4\xdd\t\xf7\xf8\x1b!\x08\xcf\x85\xbe9\x10\xbf\xbb E\x04=<\xf3\xaa\x96\x19\xb6;\xa9#\xac\xda\xe1N<\xbcZ\x9b\x16\xc8;\x9aN3\xe3\xd8\x8d\x1a\xf6\xc4\x15Is\xff\xaa\x8c\xa0\x8aH\xf9d\x05d\x13\xa6%Q\xffF(2\x9c;\xc86\xdf\xc1Hs\xb5\x97\xf2#\xffLKn\x17\xcc\x06,\xd6k4\xc4u\xb3\xe2r\xec\xf4z\x88fE~\xb4b\xfb!\x16\xf9\x13MD3iT\xdc\xaa\xed;\x1aF"\xfe\xc7\x80k\xe7\x1dG9\xa8\xf4c\'\xe8\xf4\x1c\xc1H\xf2:C}\xaf\xb5eu\xc3', 6: b'\x06'}})
```

### Verification

The verification sequence is initiated by the client by sending a frame with type `PV_Start`. The following messages always use `PV_Next` as frame type. A typical flow looks like this (details below):

<code class="diagram">
sequenceDiagram
    autonumber
    Client->>ATV: M1: Pair-Verify Start (0x04)
    Note over Client,ATV: _pd: State=M1, Pubkey
    ATV->>Client: M2: Pair-Verify Next (0x05)
    Note over ATV,Client: _pd: State=M2, Pubkey, EncryptedData
    Client->>ATV: M3: Pair-Verify Next (0x05)
    Note over Client,ATV: _pd: State=M3, EncryptedData
    ATV->>Client: M4: Pair-Verify Next (0x05)
    Note over ATV,Client: _pd: State=M4
</code>

#### Client -> ATV: M1: Pair-Verify Start (0x05)
A client initiates a verification request by sending a `PV_Start` message (M1) containing
a public key for the new session.

Example data:
```raw
Hex:
05000033E2435F7064912506010103206665D845056F6D32584C8D213EB2E8B365F569084D5006268FDD9B818028FB23455F617554790C

Decoded:
frame_type=<FrameType.PV_Start: 5>, length=51, data={'_pd': b'\x06\x01\x01\x03 fe\xd8E\x05om2XL\x8d!>\xb2\xe8\xb3e\xf5i\x08MP\x06&\x8f\xdd\x9b\x81\x80(\xfb#', '_auTy': 4}
```

#### ATV -> Client: M2: Pair-Verify Next (0x06)
When the Apple TV receives `M1`, it will respond with its session public key as well as
encrypted data used by the client to perform client verification in `M2`.

Example data:
```raw
Hex:
060000a6e1435f7064919f0578b5ecac3ecc240c38ac4c46c6b532bec01ffbb24390c45c19eabf5742bb0ad231983b8f7b42ae849494159e1240784c7d90edcf93fbe341bb3a36c66689a7cd690fbe5f0d7bcef2475c3510fb97da70452c61cf92af9e81d1549e28d56092720db5dce884c7739edaa0558c90078a286ae64d388215293b2e0601020320452357b145e149d20d91cd11f29475be78659279c67d4f9a1f04e0d56542de6b

Decoded:
frame_type=<FrameType.PV_Next: 6>, length=166, data={'_pd': b'\x05x\xb5\xec\xac>\xcc$\x0c8\xacLF\xc6\xb52\xbe\xc0\x1f\xfb\xb2C\x90\xc4\\\x19\xea\xbfWB\xbb\n\xd21\x98;\x8f{B\xae\x84\x94\x94\x15\x9e\x12@xL}\x90\xed\xcf\x93\xfb\xe3A\xbb:6\xc6f\x89\xa7\xcdi\x0f\xbe_\r{\xce\xf2G\\5\x10\xfb\x97\xdapE,a\xcf\x92\xaf\x9e\x81\xd1T\x9e(\xd5`\x92r\r\xb5\xdc\xe8\x84\xc7s\x9e\xda\xa0U\x8c\x90\x07\x8a(j\xe6M8\x82\x15);.\x06\x01\x02\x03 E#W\xb1E\xe1I\xd2\r\x91\xcd\x11\xf2\x94u\xbexe\x92y\xc6}O\x9a\x1f\x04\xe0\xd5eB\xdek'}
```

#### Client -> ATV: M3: Pair-Verify Next (0x06)
The client verifies the identity of the Apple TV based on the encrypted data and responds with
corresponding data in `M3` back to the Apple TV.

Example data:
```raw
Hex:
06000084E1435F7064917D06010305786A89ECD933472C940493C34A6AD36E936B6AB49741390864E9EFCF029BCB0EFC599EA61E5FD5A55BA6D274D6DF0F1AB6ADCB9520DAC43645E8B757175E1BBF6F032D611918B8E18639703CFACD2FB2A330745EC09DD7F91235E2AA17A58D08C5E7FB52ADE66B170627C3490F517882C833E85127087C4D1A

Decoded:
frame_type=<FrameType.PV_Next: 6>, length=132, data={'_pd': b"\x06\x01\x03\x05xj\x89\xec\xd93G,\x94\x04\x93\xc3Jj\xd3n\x93kj\xb4\x97A9\x08d\xe9\xef\xcf\x02\x9b\xcb\x0e\xfcY\x9e\xa6\x1e_\xd5\xa5[\xa6\xd2t\xd6\xdf\x0f\x1a\xb6\xad\xcb\x95 \xda\xc46E\xe8\xb7W\x17^\x1b\xbfo\x03-a\x19\x18\xb8\xe1\x869p<\xfa\xcd/\xb2\xa30t^\xc0\x9d\xd7\xf9\x125\xe2\xaa\x17\xa5\x8d\x08\xc5\xe7\xfbR\xad\xe6k\x17\x06'\xc3I\x0fQx\x82\xc83\xe8Q'\x08|M\x1a"}
```

#### ATV -> Client: M4: Pair-Verify Next (0x06)
If the client is verified properly, `M4` is sent back without an error code.

Example data:
```raw
Hex:
Data=06000009e1435f706473060104

Decoded:
frame_type=<FrameType.PV_Next: 6>, length=9, data={'_pd': b'\x06\x01\x04'}
```

### Encryption

After verification has finished, all following messages are encrypted using the derived shared
key. Chacha20Poly1305 is used for encryption (just like HAP) with the following attributes:

* Salt: *empty string*
* Info: `ServerEncrypt-main` for decrypting (incoming), `ClientEncrypt-main` for encrypting (outgoing)

Sequence number (starting from zero) is used as nonce, incremented by one for each sent or
received message and encoded as little endian (12 bytes). Individual counters are used for each
direction. AAD should be set to the frame header. Do note that encrypting data will add a 16 byte
authentication tag at the end, increasing the size by 16 bytes. The AAD for three bytes of data
with `E_OPACK` as frame type would yield `0x08000013` as AAD for both encryption and decryption.

### E_OPACK

Several types of data can be carried over the Companion protocol, but the one called `E_OPACK`
seems to be the one of interest for pyatv. It carries information for both the Apple TV remote
widget in Action Center as well as the Shortcuts app. So far, not much is known about the format
used by `E_PACK`, but what is known is documented here.

Lets start with a typical message (most data obfuscated or left out):

```raw
"Send OPACK":{
   "_i":"_systemInfo",
   "_x":1499315511,
   "_btHP":false,
   "_c":{
      "_pubID":"11:89:AA:A7:C9:F2",
      "_sv":"230.1",
      "_bf":0,
      "_siriInfo":{
         "collectorElectionVersion":1.0,
         "deviceCapabilities":{
            "seymourEnabled":1,
            "voiceTriggerEnabled":2
         },
         "sharedDataProtoBuf":"..."
      },
      "_stA":[
         "com.apple.LiveAudio",
         "com.apple.siri.wakeup",
         "com.apple.Seymour",
         "com.apple.announce",
         "com.apple.coreduet.sync",
         "com.apple.SeymourSession"
      ],
      "_sigHKU":"",
      "_clFl":128,
      "_idsID":"5EFE874C-9681-4BFE-BB7B-E9B90776730A",
      "_hkUID":[
         "0ADF154C-A2D6-4641-90F0-F4F851A52111"
      ],
      "_dC":"1",
      "_sigRP":"...",
      "_sf":256,
      "model":"iPhone10,6",
      "name":"Pierres iPhone",
      "_idHKU":"F9E5990A-F2A6-4E6D-A340-6D40BFF6BF87"
   },
   "_t":2
}
```

There's a lot of information stuffed in there, but the main elements are these ones:

| **Tag** | **Name** | **Description** |
| _i | ID | Identifier for the message request or event, e.g. `_systemInfo` or `_launchApp`. |
| _c | Content | Additional data/arguments passed to whatever is specified in `_i`. |
| _t | Type | Type of message: 1=event, 2=request, 3=response |
| _x | XID | Likely "transfer ID". The response will contain the same XID as was specified in the request. Not used by all frame types (e.g. not by authentication frames). Integer with unknown range. |
| _sid | Session ID | Identifier used by sessions. |

Most messages seems to include the tags above. Here are a few other tags seen as well:

| **Tag** | **Name** | **Description** |
| _em | Error message | In case of error, e.g. `No request handler` if no handler exists for `_i` (i.e. invalid value for `_i`).
| _ec | Error code | In case of error, e.g. 58822 |
| _ed | Error domain | In case of error, e.g. RPErrorDomain |

#### Sessions (_sessionStart, _sessionStop)

When a client connects, it can establish a new session by sending `_sessionStart`. It
includes a 32 bit session ID called `_sid` (assumed to be randomized by the client) and a
service type called `_srvT` (endpoint the client wants to talk to):

```javascript
{
    '_i': '_sessionStart',
    '_x': 123,
    '_t': '2',
    '_c': {
        '_srvT': 'com.apple.tvremoteservices',
        'sid': 123456
    }
}
```

The server will respond with a remote `_sid` upon success:

```javascript
{
    '_c': {
        '_sid': 1443773422
    },
    '_t': 3,
    '_x': 123
}
```

A final 64 bit session ID is then created by shifting up the received `_sid` 32 bits
and OR'ing it with the randomized `_sid`:

```python
(1443773422 << 32) | 123456 = 6200959630324130368 = 0x560E3BEE0001E240
```

This identifier is then used in further requests where `_sid` is required, e.g. when stopping
the session:

```javascript
// Request
{
    '_i': '_sessionStop',
    '_x': 123,
    '_t': '2',
    '_c': {
        '_sid': 6200959630324130368
    }
}

// Response
{
    '_c': {},
    '_t': 3,
    '_x': 123
}
```

Combining both endpoint session ids into a single identifier is likely for convenience
reasons.

Some commands will not work until a session has been started. One example is `_launchApp`,
which won't work after the Apple TV has been restarted until the app list has been requested
by, e.g., the shortcuts app. The theory is that the `rapportd` process (implementing
the Companion protocol) acts like a proxy between clients and processes on the system.
When a client wants to call a function (e.g. `_launchApp`) handled by another process,
`_sessionStart` will make sure that function is available to call by setting up a session
to the process handling the function and relaying messages back and forth:

<code class="diagram">
sequenceDiagram
    Client->>rapportd: _startSession: {_srvT=com.apple.tvremoteservices, _sid=123456}
    rect rgb(0, 0, 255, 0.1)
      Note over rapportd,tvremoteservices: Only if no previous session?
      rapportd->>tvremoteservices: Start new session
      tvremoteservices->>rapportd: {_sid: 1443773422}
    end
    rapportd->>Client: {_sid: 1443773422}
    note over Client, rapportd: Interaction
    Client->>rapportd: _stopSession: {_sid=6200959630324130368}
    rapportd->>Client: {}
</code>

Once a command has been called, it will be cached making it possible to call it without
sending `_sessionStart` again. This is probably why `_launchApp` keeps working after
requesting the list from Shortcuts (as it will set up a new session).

#### Events

It is possible to subscribe to events using `_interest`:


```javascript
{
    '_i': '_interest',
    '_x': 123,
    '_t': '1,
    '_c': {
        '_regEvents: ['_iMC']
    }
}
```

No explicit response is sent to the request, other than an event update. So far `_iMC`
(Media Control) is the only known event type. An event update might look like this:

```javascript
{
    '_i': '_iMC',
    '_x': 123,
    '_c': {
        '_mcF': 256
    },
    '_t': 1}
```

The Media Control Flags (`mcF`) chunk is a bitmask with the following bits (not fully reversed
 yet):

| Bitmask | Purpose |
| ------- | ------- |
| 0x0001  | Play
| 0x0002  | Pause
| 0x0004  | Previous track
| 0x0008  | Next track
| 0x0010  | Fast forward
| 0x0020  | Rewind
| 0x0040  | ?
| 0x0080  | ?
| 0x0100  | Volume
| 0x0200  | Skip forward (e.g. 30 seconds, defined by player)
| 0x0400  | Skip backward (e.g. 30 seconds, defined by player)

To unsubscribe, instead use `_deregEvents`:

```javascript
{
    '_i': '_interest',
    '_x': 123,
    '_t': 1,
    '_c': {
        '_deregEvents': ['_iMC']
    }
}
```

#### Launch Application (_launchApp)

```javascript
// Request
{'_i': '_launchApp', '_x': 123, '_t': '2', '_c': {'_bundleID': 'com.netflix.Netflix'}}

// Response
{'_c': {}, '_t': 3, '_x': 123}
```

#### Fetch Application List (FetchLaunchableApplicationsEvent)

```javascript
// Request
{'_i': 'FetchLaunchableApplicationsEvent', '_x': 123, '_t': '2', '_c': {}}

// Response
{'_c': {'com.apple.podcasts': 'Podcaster', 'com.apple.TVMovies': 'Filmer', 'com.apple.TVWatchList': 'TV', 'com.apple.TVPhotos': 'Bilder', 'com.apple.TVAppStore': 'App\xa0Store', 'se.cmore.CMore2': 'C More', 'com.apple.Arcade': 'Arcade', 'com.apple.TVSearch': 'Sök', 'emby.media.emby-tvos': 'Emby', 'se.tv4.tv4play': 'TV4 Play', 'com.apple.TVHomeSharing': 'Datorer', 'com.google.ios.youtube': 'YouTube', 'se.svtplay.mobil': 'SVT Play', 'com.plexapp.plex': 'Plex', 'com.MTGx.ViaFree.se': 'Viafree', 'com.apple.TVSettings': 'Inställningar', 'com.apple.appleevents': 'Apple Events', 'com.kanal5.play': 'discovery+', 'com.netflix.Netflix': 'Netflix', 'se.harbourfront.viasatondemand': 'Viaplay', 'com.apple.TVMusic': 'Musik'}, '_t': 3, '_x': 123}
```

#### Buttons/Commands (_hidC)

Identifier shall be set to *_hidC* and content (*_c*), to the following:

| **Tag** | **Name** | **Value** |
| _hBtS | Button state | 1=Down/pressed, 2=Up/released |
| _hidC | Command | 1=Up<br/>2=Down<br/>3=Left<br/>4=Right<br/>5=Menu<br/>6=Select<br/>7=Home<br/>8=Volume up<br/>9=Volume down<br/>10=Siri<br/>11=Screensaver<br/>12=Sleep<br/>13=Wake<br/>14=PlayPause<br/>15=Channel Increment<br/>16=Channel Decrement<br/>17=Guide<br/>18=Page Up<br/>19=Page Down

Example: Put device to sleep:

```javascript
// Request
{'_i': '_hidC', '_x': 123, '_t': '2', '_c': {'_hBtS': 2, '_hidC': 12}}

// Response
{'_c': {}, '_t': 3, '_x': 123}
```

#### Touch gestures

Additional information about slide gestures : slide gestures are handled with a succession of events with about 20ms between each requests
 
1. First event with _tPh=1 (press mode)
2. N requests with _tPh = 3 (where N*100 ms = duration of the gesture), with _cx and _cy coordinates changing at each request
3. One last request with _tPh=4 when released

To be noted :
- _cx and _cy coordinates must be in the range [0,1000] which is set in a startup event _touchStart :
```javascript
// Received during initialization
 {'_i': '_touchStart', '_x': 1865081428, '_btHP': False, '_c': {'_height': 1000.0, '_tFl': 0, '_width': 1000.0}, '_t': 2}
 ```
- _ns = timestamp in nanoseconds (probably based on device boot time)
- when reaching the edge of the touch area, a release event should be sent with a new press event otherwise the cursor will move in the opposite way 


#### Single tap

3 requests have to be sent to simulate tap gesture on the touch pad : 2 commands requests (_hidC) and 1 event request (_hidT)
- 2 requests with _i = _hidC and in the additional arguments structure _C :
  - the button pressed : _hidC = 6 for touch pad click
  - the action mode : _hBtS = 1 for press, and the second request with _hBtS = 2 for release
-  1 event with additional arguments as followed :
  - _cx and _cy (x,y coordinates) set to max : 1000
  - _tPh : action mode of the touchpad set to 5

```javascript
// Request
{'_i': '_hidC', '_x': 1984212224, '_btHP': False, '_c': {'_hBtS': 1, '_hidC': 6}, '_t': 2}
{'_i': '_hidC', '_x': 1984212225, '_btHP': False, '_c': {'_hBtS': 2, '_hidC': 6}, '_t': 2}
{'_i': '_hidT', '_x': 1984212226, '_c': {'_ns': 713243707438041, '_tFg': 1, '_cx': 1000, '_tPh': 5, '_cy': 1000}, '_t': 1}

// Response
R: {'_c': {}, '_t': 3, '_x': 1984212224}
R: {'_c': {}, '_t': 3, '_x': 1984212225}
```


#### Gestures

Touch gestures are a series of events (_i = "_hidT", _t = 1) sent every few milliseconds (~20ms) with updated x,y coordinates
- 1 start event with _tPh = 1 (pressed event)
- N events with _tPh = 3 (hold)
- 1 end event with _tPh = 4 (released)

```javascript
// Request
{'_i': '_hidT', '_x': 588648840, '_c': {'_ns': 713018028759791, '_tFg': 1, '_cx': 500, '_tPh': 1, '_cy': 800}, '_t': 1}
{'_i': '_hidT', '_x': 588648841, '_c': {'_ns': 713018124653791, '_tFg': 1, '_cx': 506, '_tPh': 3, '_cy': 789}, '_t': 1}
{'_i': '_hidT', '_x': 588648842, '_c': {'_ns': 713018141323791, '_tFg': 1, '_cx': 520, '_tPh': 3, '_cy': 767}, '_t': 1}
{'_i': '_hidT', '_x': 588648843, '_c': {'_ns': 713018157994791, '_tFg': 1, '_cx': 520, '_tPh': 3, '_cy': 758}, '_t': 1}
...
{'_i': '_hidT', '_x': 588648930, '_c': {'_ns': 713019612448791, '_tFg': 1, '_cx': 587, '_tPh': 3, '_cy': 128}, '_t': 1}
{'_i': '_hidT', '_x': 588648931, '_c': {'_ns': 713019616615791, '_tFg': 1, '_cx': 593, '_tPh': 4, '_cy': 134}, '_t': 1}
```


#### System Status

A system can be in one of the following states:

| **ID** | **State** | **Note** |
| 0x01 | Asleep | Device is sleeping/in standby.
| 0x02 | Screensaver | Screensaver is shown on screen.
| 0x03 | Awake | Device is awake.
| 0x04 | Idle | This state has not been seen, but is likely present. Not sure what difference is compare to `Awake`.

Current system state can be fetch using `FetchAttentionState`:

```javascript
// Request
{'_i': 'FetchAttentionState', '_t': 2, '_c': {}, '_x': 38571}

// Response
{'_c': {'state': 1}, '_t': 3, '_x': 38571}
```

`state` in the response maps to **ID** in the table above.

Updates to the state is announced via the `SystemStatus` event:

```javascript
// Register to event
{'_i': '_interest', '_t': 1, '_c': {'_regEvents': ['SystemStatus']}, '_x': 38573}

// Example of an event
{'_i': 'SystemStatus', '_x': 798413326, '_c': {'state': 3}, '_t': 1}
```

# AirPlay

The AirPlay protocol suite is used to stream media from a sender to a receiver. Two protocols
are used: AirTunes and "AirPlay". The former is used for audio streaming and is based on
*Real-Time Streaming Protocol*. The latter adds video and image capabilities to the stack,
allowing video streaming, screen mirroring and image sharing.

There's quite a history behind the AirPlay stack and I haven't fully grasped it yet. But I
*think* it looks something like this:

<code class="diagram">
graph LR
    AT[AirTunes, 2004] --> AT2(AirTunes v2, 2010)
    AT2 --> APS1
    AP1[AirPlay, 2010] --> APS1
    APS1[AirPlay v1, 2010] --> APS2
    APS2[AirPlay v2, 2018]
</code>

AirTunes (i.e. Airplay v1) is announced as *Remote Audio Output Protocol*, e.g. when looking at Zeroconf
services. That's also what it will be referred to here.

As the AirPlay protocol is covered a lot elsewhere, I will update here when I'm bored. Please
refer to the references for more details on the protocol.

## Service Discovery

AirPlay uses two services, one for audio and one for video. They are described here.

### RAOP

| **Property** | **Example value** | **Meaning** |
| ------------ | ----------------- | ----------- |
| et           | 0,4               | Encryption type: 0=unencrypted, 1=RSA (AirPort Express), 3=FairPlay, 4=MFiSAP, 5=FairPlay SAPv2.5
| da           | true              | Digest Authentication
| ss           | 16                | Audio sample size in bits
| am           | AppleTV6,2        | Apple (device) Model
| tp           | TCP,UDP           | Supported transport protocols for media streams
| pw           | false             | Password protected
| fv           | s8927.1096.0      | Firmware version (non-Apple)
| txtvers      | 1                 | TXT record version 1
| vn           | 65537             | Version Number (uint16.uint16, e.g. 1.1 = 65537)
| md           | 0,1,2             | Supported metadata: 0=text, 1=artwork, 2=progress (only for pre iOS7 senders)
| vs           | 103.2             | Server version
| sv           | false             | Software Volume, whether receiver needs sender to adjust their volume.
| sm           | false             | Software Mute, (as above).
| ch           | 2                 | Number of audio channels
| sr           | 44100             | Audio sample rate
| cn           | 0,1               | Audio codecs: 0=PCM, 1=AppleLossless (ALAC), 2=AAC, 3=AAC ELD, 4=OPUS
| ov           | 8.4.4             | Operating system version? (seen on ATV 3)
| pk           | 38fd7e...         | Public key
| pw           | false             | Whether password (PIN) auth is required. Triggers Method POST Path /pair-pin-start from sender
| ft           | 0x8074...         | Supported Features (hex integer bitmask)
| sf           | 0x387e...         | System Flags (hex integer bitmask)



### AirPlay

| **Property** | **Example value**     | **Meaning** |
| ------------ | --------------------- | ----------- |
| features     | 0x4A7FDFD5,0x3C155FDE | Features supported by device, see [here](https://openairplay.github.io/airplay-spec/features.html)
| igl | 1 | Is Group Leader
| model | AppleTV6,2 | Model name
| osvers | 14.5 | Operating system version
| pi | UUID4 | Group ID
| vv | 2 | ?
| srcvers | 540.31.41 | AirPlay version
| psi | UUID4 | Public AirPlay Pairing Identifier
| gid | UUID4 | Group UUID
| pk  | UUID4 | Public key
| acl | 0 | Access Control Level
| deviceid | AA:BB:CC:DD:EE:FF | Device identifier, typically MAC address
| protovers | Protocol version
| fex | 1d9/St5fFTw | ?
| gcgl | 1 | Group Contains Group Leader
| flags | 0x244 | Status flags, see [here](https://openairplay.github.io/airplay-spec/status_flags.html)
| btaddr | AA:BB:CC:DD:EE:FF | Bluetooth address

## RAOP

This section covers the audio streaming part of AirPlay, i.e. AirTunes/RAOP. TBD

### RTSP

Streaming sessions are set up using the RTSP protocol. This section covers the basics of how
that is done.

#### OPTIONS

Sender asks receiver what methods it supports:

**Sender -> Receiver:**
```raw
OPTIONS * RTSP/1.0
CSeq: 0
nUser-Agent: AirPlay/540.31
DACP-ID: A851074254310A45
Active-Remote: 4019753970
Client-Instance: A851074254310A45
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 17:35:10 GMT
Content-Length: 0
Public: ANNOUNCE, SETUP, RECORD, PAUSE, FLUSH, TEARDOWN, OPTIONS, GET_PARAMETER, SET_PARAMETER, POST, GET, PUT
Server: AirTunes/540.31.41
CSeq: 0
```

#### ANNOUNCE

Sender tells the receiver about properties for an upcoming stream.

**Sender -> Receiver:**
```raw
ANNOUNCE rtsp://10.0.10.254/4018537194 RTSP/1.0
CSeq: 0
User-Agent: AirPlay/540.31
DACP-ID: 9D881F7AED72DB4A
Active-Remote: 3630929274
Client-Instance: 9D881F7AED72DB4A
Content-Type: application/sdp
Content-Length: 179

v=0
o=iTunes 4018537194 0 IN IP4 10.0.10.254
s=iTunes
c=IN IP4 10.0.10.84
t=0 0
m=audio 0 RTP/AVP 96
a=rtpmap:96 AppleLossless
a=fmtp:96 352 0 16 40 10 14 2 255 0 0 44100
```

Some observations (might not be true):

* ID in `o=` property (`4018537194`) seems to match what is used for rtsp endpoint (`rtsp://xxx/4018537194`)
* Address in `o=` corresponds to IP address of the sender
* Address in `c=` is address of the receiver
* Configuration for ALAC is used here. Format for `fmtp` is `a=fmtp:96 <frames per packet> <ALAC version, 0> <ALAC sample size> <ALAC history mult> <ALAC initial history> <ALAC rice limit> <ALAC channel count> <ALAC max run> <ALAC max coded frame size, 0 for auto/unknown> <ALAC average bitrate, 0 for auto> <ALAC sample rate>`

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 17:25:54 GMT
Content-Length: 0
Server: AirTunes/540.31.41
CSeq: 0
```

#### SETUP

Sender requests initialization of a (Airplay v1) session (but does not start it). Sets up three different UDP channels:

| Channel | Description |
| ------- | ----------- |
| server  | audio
| control | sync and retransmission of lost frames
| timing  | sync of common master clock

**Sender -> Receiver:**
```raw
SETUP rtsp://10.0.10.254/1085946124 RTSP/1.0
CSeq: 2
User-Agent: AirPlay/540.31
DACP-ID: A851074254310A45
Active-Remote: 4019753970
Client-Instance: A851074254310A45
Transport: RTP/AVP/UDP;unicast;interleaved=0-1;mode=record;control_port=55433;timing_port=55081
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 17:35:11 GMT
Content-Length: 0
Transport: RTP/AVP/UDP;unicast;mode=record;server_port=55801;control_port=50367;timing_port=0
Session: 1
Audio-Jack-Status: connected
Server: AirTunes/540.31.41
CSeq: 2
```

#### SETPEERS

Describes PTP timing peers to the receiver.

```raw
...
Content-Type: /peer-list-changed

        Contains [] array of IP{4|6}addrs e.g.:
        ['::',
         '::',
         '127.0.0.1']
```

#### RECORD

Requests to start the stream at a particular point. Initially, a sequence (16bit) number and start time (32bit) are included in `RTP-Info` which correspond to those in the first RTP packet. These values are
randomized.

**Sender -> Receiver:**
```raw
RECORD rtsp://10.0.10.254/1085946124 RTSP/1.0
CSeq: 6
User-Agent: AirPlay/540.31
DACP-ID: A851074254310A45
Active-Remote: 4019753970
Client-Instance: A851074254310A45
Range: npt=0-
Session: 1
RTP-Info: seq=15432;rtptime=66150
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 07:35:11 GMT
Content-Length: 0
Audio-Latency: 3035
Server: AirTunes/540.31.41
CSeq: 6
```

#### FLUSH

Requests to flush the receivers buffer and pause/stop what is playing.

**Sender -> Receiver:**
```raw
FLUSH rtsp://10.0.10.254/1085946124 RTSP/1.0
CSeq: 7
User-Agent: AirPlay/540.31
DACP-ID: A851074254310A45
Active-Remote: 4019753970
Client-Instance: A851074254310A45
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 17:35:11 GMT
Content-Length: 0
Server: AirTunes/540.31.41
CSeq: 7
```

#### TEARDOWN

End the active session.

**Sender -> Receiver:**
```raw
TEARDOWN rtsp://10.0.10.254/1085946124 RTSP/1.0
CSeq: 8
User-Agent: AirPlay/540.31
DACP-ID: A851074254310A45
Active-Remote: 4019753970
Client-Instance: A851074254310A45
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 17:35:19 GMT
Content-Length: 0
Server: AirTunes/540.31.41
CSeq: 8
```

#### SET_PARAMETER

Change a parameter, e.g. metadata or progress, on the receiver.

**Sender -> Receiver:**
```raw
SET_PARAMETER rtsp://10.0.10.254/1085946124 RTSP/1.0
CSeq: 3
User-Agent: AirPlay/540.31
DACP-ID: A851074254310A45
Active-Remote: 4019753970
Client-Instance: A851074254310A45
Content-Type: text/parameters
Content-Length: 11

volume: -20
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Tue, 11 May 2021 17:35:11 GMT
Content-Length: 0
Server: AirTunes/540.31.41
CSeq: 3
```

## AirPlay

This section deals with the "video part" of AirPlay. TBD

### Commands

#### /auth-setup

Devices supporting MFi authentication (e.g. has `et=4`) might require an authentication step
initiated by `/auth-setup`. This is always the case for AirPlay 2. More details
[here](https://openairplay.github.io/airplay-spec/audio/rtsp_requests/post_auth_setup.html).

*TODO: document more*

The request consists of one byte encryption type (0x01: unencrypted,
0x02: MFi-SAP-encrypted AES key) and 32 bytes Curve25519 public key. Normally this step is used
to verify MFi authenticity, but no further action needs to be taken (i.e. just send request
and ignore response) for devices requiring this step. Implementation in `pyatv` has been stolen
from owntone [here](https://github.com/owntone/owntone-server/blob/c1db4d914f5cd8e7dbe6c1b6478d68a4c14824af/src/outputs/raop.c#L1568).

**Sender -> Receiver:**
```raw
POST /auth-setup RTSP/1.0
CSeq: 0
User-Agent: AirPlay/540.31
DACP-ID: BFAA2A9155BD093C
Active-Remote: 347218209
Client-Instance: BFAA2A9155BD093C
Content-Type: application/octet-stream
Content-Length: 33

015902ede90d4ef2bd4cb68a6330038207a94dbd50d8aa465b5d8c012a0c7e1d4e27
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Content-Length: 1076
Content-Type: application/octet-stream
Server: AirTunes/366.0
CSeq: 0

97a02c0d0a31486316de944d8404f4e01f93b05dde4543cc022a5727e8a352330000038c3082038806092a864886f70d010702a0820379308203750201013100300b06092a864886f70d010701a082035d3082035930820241a003020102020f1212aa121127aa00aa8023aa238776300d06092a864886f70d0101050500308183310b300906035504061302555331133011060355040a130a4170706c6520496e632e31263024060355040b131d4170706c652043657274696669636174696f6e20417574686f72697479313730350603550403132e4170706c652069506f64204163636573736f726965732043657274696669636174696f6e20417574686f72697479301e170d3132313132373138323135305a170d3230313132373138323135305a3070310b300906035504061302555331133011060355040a0c0a4170706c6520496e632e311f301d060355040b0c164170706c652069506f64204163636573736f72696573312b302906035504030c224950415f31323132414131323131323741413030414138303233414132333837373630819f300d06092a864886f70d010101050003818d003081890281810097e302c45e7b6f387dd390201b0dd902b19dc30d72a93a8b9f1313c6108e90ee93daff24177526736e4f1f58a2c2382cf4b7f7359bb1b1a3a7595850d489f335557a48653d96e9407ccc05eba6c867716e446b31d2bdc9c5122af4c213e7d7f0635b74e323094483a900bd3f93ce8833785b2fd14d88fb2dd4c581e1189b38250203010001a360305e301d0603551d0e04160414d74ea8b90475ee5140d2be7d2f9258931c7543cb300c0603551d130101ff04023000301f0603551d23041830168014ff4b1a439af51996ab18002b61c9ee409d8ec704300e0603551d0f0101ff0404030203b8300d06092a864886f70d0101050500038201010012e8b29b1e1b81e7a14b6435b92a9c58f0a28e6bcb645edd223969b77a70dda3ddc280562f53cb87e3ccd5fea213ccc9c2a4f005c3aa4447b84a895df649f74e9f6612d6cc69eeb7561706fa718f5e1d80b0554affe911c6fa3f99ca06bcf4debf03b64449bde16058392c830be55ae33273d24eecaf0f4aef6f6c46bed87192e2773e5ae092098b32563a532164df5eecd3fc299c8b267cf555b516b02a013920242f4162e6cb5d8d555356d3999c989860ed8c4ea2a0f34af4bcc74b864a07c6d952115dd28b0cc5d8bc780567dcaafc721e678391a048b00cf8664d5c0ad1949b57165a7c98144480ac0510a1887e27821d966b14478c901f6c7548f8563e310000000080121b14309c641bc593196f886c633d19986c11ca9cb4be2fdad1f2ec1427eeb8da23aaeaf7a713f2b8e05a6942db364e3dd408d5a1eeb1525baadc5ccb46614dadef1bfa565c65f46a54f576802209faa39ac442ac7cd43995be833f7794d0517fd93218e86c0228b30b036d3055476114d926de2875bed7cef4970492df58a3
```

## References

[RAOP-Player](https://github.com/philippe44/RAOP-Player)

[owntone-server](https://github.com/owntone/owntone-server)

[Unofficial AirPlay Specification](https://openairplay.github.io/airplay-spec/introduction.html)

[AirPlay 2 Internals](https://emanuelecozzi.net/docs/airplay2)

[Using raw in ALAC frames (Stackoverflow)](https://stackoverflow.com/questions/34584522/airplay-protocol-how-to-use-raw-pcm-instead-of-alac)

[Unofficial AirPlay Protocol Specification](https://nto.github.io/AirPlay.html)

[AirTunes v2](https://git.zx2c4.com/Airtunes2/about/)

[AirPlayAuth](https://github.com/funtax/AirPlayAuth)

# AirPlay 2

In reality, AirPlay 2 has a lot in common with its predecessor, but a lot also differs
so it deserves its own chapter.

For now, the main focus here is to describe how AirPlay can be set up for remote control
only, i.e. how to get metadata for what is playing. Other parts will be added later.

## Service Discovery

TBD

## Authentication

There are multiple ways to authenticate a device, all based on HAP just like Companion
and MRP. Implementations of regular pairing and transient pairing (written in C) can
be found [here](https://github.com/ejurgensen/pair_ap).

*TBD: Add details regarding pairing and encryption.*

### Encryption
All channels described here are encrypted using Chacha20Poly1305. The session key is always
derived (with HKDF) from the shared secret agreed upon during authentication. Salt and info
values vary depending on channel.

Data is encrypted in blocks, with a two byte (little-endian) size field prepended to it
as well as a 16 byte auth tag appended:

| **Size (2 bytes)** | **Data (n bytes)** | **Auth tag (16 bytes)** |

HomeKit madates a maximum block size of 1024 bytes. This is not the case here as any block
size (that fits length tag) can be used.

This is also described in the HAP specification, section 5.2.2 (Release R1).

## Remote Control

*NB: This is a WIP. Far from everything is understood yet, so take this part with a pinch
of salt.*

Setting up a remote control session works more or less like setting up a regular audio
stream, but it has a different type and the data channel will carry control messages.
Below is a sequence diagram outlining the setup flow on a higher level. Three channels
are used: control, event and data. You should interpret *Control Sender* as the control
channel on the "sender" side, e.g. an iPhone.

<code class="diagram">
sequenceDiagram
    participant CS as Control Sender
    participant CR as Control Receiver
    participant ES as Event Sender
    participant ER as Event Receiver
    participant DS as Data Sender
    participant DR as Data Receiver
    CS->>CR: SETUP {isRemoteControlOnly: True}
    CR->>CS: OK {eventPort}
    CS-->>ES: Start Event Sender
    ES->>ER: Connect (eventPort)
    ER-->>ES: 
    CS->>CR: RECORD
    CR->>CS: OK
    ER->>ES: System info update
    CS->>CR: SETUP (stream)
    CR->>CS: OK {dataPort}
    CS-->>DS: Start Data Sender
    DS->>DR: Connect (dataPort)
    DR-->>DS: 
    note over DS,DR: Exchange messages here
    loop Every two seconds
        CS->>CR: POST /feedback
        CR->>CS: OK
    end
</code>

### Control Channel (RTSP)
This section describes how a remote control session is set up on the main (control) channel.
An event and data channel will be set up in parallel, so be prepared to skip back and forth
between chapters a bit to understand what's going on. Keep the sequence diagram above ready
at hand.

The sender starts by setting up a new session, requesting a remote control session via
`isRemoteControlOnly`:

**Sender -> Receiver:**
```raw
SETUP rtsp://10.0.10.254/14511846595692938970 RTSP/1.0
Content-Length: 376
Content-Type: application/x-apple-binary-plist
CSeq: 7
User-Agent: AirPlay/550.10

bplist00\xdb\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16_\x10\x13isRemoteControlOnlyVosName]sourceVersion^timingProtocolUmodelXdeviceIDYosVersion^osBuildVersionZmacAddress[sessionUUIDTname\tYiPhone OSV550.10TNoneZiPhone10,6_\x10\x11FF:EE:DD:CC:BB:AAV14.7.1U18G82_\x10\x11AA:BB:CC:DD:EE:FF_\x10$C9646F97-7B3D-46DA-9F92-332ED10EC258^Pierres iPhone\x00\x08\x00\x1f\x005\x00<\x00J\x00Y\x00_\x00h\x00r\x00\x81\x00\x8c\x00\x98\x00\x9d\x00\x9e\x00\xa8\x00\xaf\x00\xb4\x00\xbf\x00\xd3\x00\xda\x00\xe0\x00\xf4\x01\x1b\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x00\x17\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01*
```

The decoded content looks like this:

```javascript
{'isRemoteControlOnly': True, 'osName': 'iPhone OS', 'sourceVersion': '550.10', 'timingProtocol': 'None', 'model': 'iPhone10,6', 'deviceID': 'FF:EE:DD:CC:BB:AA', 'osVersion': '14.7.1', 'osBuildVersion': '18G82', 'macAddress': 'AA:BB:CC:DD:EE:FF', 'sessionUUID': 'C9646F97-7B3D-46DA-9F92-332ED10EC258', 'name': 'Pierres iPhone'}
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Fri, 20 Aug 2021 17:09:58 GMT
Content-Length: 59
Content-Type: application/x-apple-binary-plist
Server: AirTunes/550.10
CSeq: 7

bplist00\xd1\x01\x02YeventPort\x11\xc0\xba\x08\x0b\x15\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18'
```

Which decodes to:

```javascript
{'eventPort': 49338}
```

At this stage, the receiver expects the sender to establish a TCP connection to the port specified
by `eventPort`. This connection will be used for regular AirPlay events, i.e. RTSP messages
are exchanged here. See the next chapter for more details.

After the sender has connected to the event port, it shall start the stream using `RECORD`
(iOS seems to request `/info` before doing this, that's why CSeq 8 is skipped):

**Sender -> Receiver:**
```raw
RECORD rtsp://10.0.10.254/14511846595692938970 RTSP/1.0
CSeq: 9
User-Agent: AirPlay/550.10
```

The receiver will respond with:

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Thu, 19 Aug 2021 20:17:58 GMT
Content-Length: 0
Audio-Latency: 0
Server: AirTunes/550.10
CSeq: 9
```

Now the receiver will send a "system info update" on the event channel.

The next step is to set up a channel for the actual remote control messages:

**Sender -> Receiver:**
```raw
SETUP rtsp://10.0.10.254/14511846595692938970 RTSP/1.0
Content-Length: 298
Content-Type: application/x-apple-binary-plist
CSeq: 10
User-Agent: AirPlay/550.10

bplist00\xd1\x01\x02Wstreams\xa1\x03\xd7\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11[controlTypeYchannelIDTseedZclientUUIDTtype_\x10\x14wantsDedicatedSocket^clientTypeUUID\x10\x02_\x10$DA6501B1-1452-4417-AE27-ED8E309DEBCE\x13\xd0_\x18\xd7\x13\xcbh\xd6_\x10$11F965B7-8653-4A25-B82E-D9416C05FE68\x10\x82\t_\x10$1910A70F-DBC0-4242-AF95-115DB30604E1\x08\x0b\x13\x15$0:?JOfuw\x9e\xa7\xce\xd0\xd1\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf8
```

Which decodes to:

```javascript
{'streams': [{'controlType': 2, 'channelID': 'DA6501B1-1452-4417-AE27-ED8E309DEBCE', 'seed': -3431997079003895594, 'clientUUID': '11F965B7-8653-4A25-B82E-D9416C05FE68', 'type': 130, 'wantsDedicatedSocket': True, 'clientTypeUUID': '1910A70F-DBC0-4242-AF95-115DB30604E1'}]}
```

Some things to note here:

* `channelID` and `clientUUID` change each time, so they are likely randomized
* `clientTypeUUID` of `1910A70F-DBC0-4242-AF95-115DB30604E1` means Media Remote (there
  are a few other values used under other circumstances, like `8186BE43-A39A-4C42-9D0E-60BDB9CE1FE3`).
* `type` 130 represents the Remote Control type
* `seed` is used when deriving encryption keys for the channel, if encryption is mandated.

The response looks like this:

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Thu, 19 Aug 2021 20:17:58 GMT
Content-Length: 100
Content-Type: application/x-apple-binary-plist
Server: AirTunes/550.10
CSeq: 10

bplist00\xd1\x01\x02Wstreams\xa1\x03\xd3\x04\x05\x06\x07\x08\tTtypeXstreamIDXdataPort\x10\x82\x10\x01\x11\xc0\xae\x08\x0b\x13\x15\x1c!*357\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\n\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00:
```

Which decodes to:

```javascript
{'streams': [{'type': 130, 'streamID': 1, 'dataPort': 49326}]}
```

Like with the event channel, the sender is expected to establish a TCP connection to
`dataPort` and enable encryption. Remote control messages should from now on be exchanged on the
data channel.

The sender shall continuously send feedback updates to the receiver on the control channel:

**Sender -> Receiver:**
```raw
POST /feedback RTSP/1.0
CSeq: 12
User-Agent: AirPlay/550.10
```

**Receiver -> Sender:**
```raw
RTSP/1.0 200 OK
Date: Thu, 19 Aug 2021 20:18:08 GMT
Content-Length: 55
Content-Type: application/x-apple-binary-plist
Server: AirTunes/550.10
CSeq: 12

bplist00\xd1\x01\x02Wstreams\xa0\x08\x0b\x13\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14
````

Which decodes to this:

```javascript
{'streams': []}
```

iOS sends this every two seconds as a keep-alive.

**Now it's done!**

### Event Channel
The event channel is initiated by the sender to the port returned in the response to `SETUP`.
After `SETUP` has finished, the sender shall connect to this port (TCP) and enable encryption.
The following parameters are used to derive encryption keys:

| Direction | Salt | Info |
| --------- | ---- | ---- |
| Output    | Events-Salt | Events-Write-Encryption-Key |
| Input     | Events-Salt | Events-Read-Encryption-Key |

Even though the channel setup is initiated by the sender, the channel should be treated as
originating from the receiver. This means that input and output keys shall be reversed on
the sender side (use `Output` as `Input` and `Input` as `Output` to SRP).

After the stream has been started using `RECORD`, the receiver will send a "system info update",
which is basically what is returned when requesting `/info`:

**Receiver -> Sender:**
```raw
POST /command RTSP/1.0
CSeq: 0
Content-Length: 1386
Content-Type: application/x-apple-binary-plist

bplist00\xd2\x01\x02\x03\x04TtypeUvalueZupdateInfo\xdf\x10\x18\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f&\'#)*+,-.&0123;#=>?@ASpsiRvv_\x10\x14playbackCapabilities_\x10\x15canRecordScreenStream[statusFlags_\x10\x18keepAliveSendStatsAsBodyTname_\x10\x0fprotocolVersion_\x10\x11volumeControlType]senderAddressXdeviceIDRpi^screenDemoMode]initialVolumeZfeaturesExZtxtAirPlay_\x10\x10supportedFormats]sourceVersion_\x10\x16hasUDPMirroringSupportUmodelRpkZmacAddress_\x10\x15receiverHDRCapabilityXfeatures_\x10$6EE2C905-874B-4B4B-A50B-0F06B1800A17\x10\x02\xd3 !"###_\x10\x15supportsInterstitials_\x10\x15supportsFPSSecureStop_\x10\x1dsupportsUIForAudioOnlyContent\t\t\t\x08\x11\x02D\tZVardagsrumS1.1\x10\x04_\x10\x1110.0.10.254:46164_\x10\x11AA:BB:CC:DD:EE:FF_\x10$de7562c4-7bd2-4005-a8e4-d584bf63161a\x08#\xc04\x00\x00\x00\x00\x00\x00[1d9/St5fFTwO\x11\x01\x7f\x05acl=0\x18btaddr=FF:EE:DD:CC:BB:AA\x1adeviceid=AA:BB:CC:DD:EE:FF\x0ffex=1d9/St5fFTw\x1efeatures=0x4A7FDFD5,0x3C155FDE\x0bflags=0x244(gid=4D826039-0F40-4605-AD11-A6516183BAA6\x05igl=1\x06gcgl=1\x10model=AppleTV6,2\rprotovers=1.1\'pi=de7562c4-7bd2-4005-a8e4-d584bf63161a(psi=6EE2C905-874B-4B4B-A50B-0F06B1800A17Cpk=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\x0esrcvers=550.10\x0bosvers=14.7\x04vv=2\xd44567899:_\x10\x15lowLatencyAudioStream\\screenStream[audioStream\\bufferStream\x10\x00\x12\x01D\x08\x00\x12\x00\xe0\x00\x00V550.10\tZAppleTV6,2O\x10 \xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa_\x10\x11AA:BB:CC:DD:EE:FFT4k30\x13<\x15_\xdeJ\x7f\xdf\xd5\x00\x08\x00\r\x00\x12\x00\x18\x00#\x00V\x00Z\x00]\x00t\x00\x8c\x00\x98\x00\xb3\x00\xb8\x00\xca\x00\xde\x00\xec\x00\xf5\x00\xf8\x01\x07\x01\x15\x01 \x01+\x01>\x01L\x01e\x01k\x01n\x01y\x01\x91\x01\x9a\x01\xc1\x01\xc3\x01\xca\x01\xe2\x01\xfa\x02\x1a\x02\x1b\x02\x1c\x02\x1d\x02\x1e\x02!\x02"\x02-\x021\x023\x02G\x02[\x02\x82\x02\x83\x02\x8c\x02\x98\x04\x1b\x04$\x04<\x04I\x04U\x04b\x04d\x04i\x04n\x04u\x04v\x04\x81\x04\xa4\x04\xb8\x04\xbd\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x00B\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xc6
```

Which decodes to this (identifiers replaced with random values):

```javascript
{'type': 'updateInfo', 'value': {'psi': '6EE2C905-874B-4B4B-A50B-0F06B1800A17', 'vv': 2, 'playbackCapabilities': {'supportsInterstitials': True, 'supportsFPSSecureStop': True, 'supportsUIForAudioOnlyContent': True}, 'canRecordScreenStream': False, 'statusFlags': 580, 'keepAliveSendStatsAsBody': True, 'name': 'Vardagsrum', 'protocolVersion': '1.1', 'volumeControlType': 4, 'senderAddress': '10.0.10.254:46164', 'deviceID': 'AA:BB:CC:DD:EE:FF', 'pi': 'de7562c4-7bd2-4005-a8e4-d584bf63161a', 'screenDemoMode': False, 'initialVolume': -20.0, 'featuresEx': '1d9/St5fFTw', 'txtAirPlay': b"\x05acl=0\x18btaddr=FF:EE:DD:CC:BB:AA\x1adeviceid=AA:BB:CC:DD:EE:FF\x0ffex=1d9/St5fFTw\x1efeatures=0x4A7FDFD5,0x3C155FDE\x0bflags=0x244(gid=4D826039-0F40-4605-AD11-A6516183BAA6\x05igl=1\x06gcgl=1\x10model=AppleTV6,2\rprotovers=1.1'pi=de7562c4-7bd2-4005-a8e4-d584bf63161a(psi=6EE2C905-874B-4B4B-A50B-0F06B1800A17Cpk=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\x0esrcvers=550.10\x0bosvers=14.7\x04vv=2", 'supportedFormats': {'lowLatencyAudioStream': 0, 'screenStream': 21235712, 'audioStream': 21235712, 'bufferStream': 14680064}, 'sourceVersion': '550.10', 'hasUDPMirroringSupport': True, 'model': 'AppleTV6,2', 'pk': b'\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa', 'macAddress': 'AA:BB:CC:DD:EE:FF', 'receiverHDRCapability': '4k30', 'features': 4329472025123872725}}
```

It is important to send a response to this request, otherwise the connection will time out after
30 seconds and be closed by the receiver:

```raw
RTSP/1.0 200 OK
Content-Length:0
Audio-Latency: 0
Server: AirTunes/550.10
CSeq: 0
```

No other message has been seen on this channel with regards to remote control support.

### Data Channel
The data channel carries messages related to the remote control. In reality, it's MRP messages
(so protobuf). The same message definitions used by Media Remote Protocol are also valid
here.

#### Encryption

The following parameters are used to derive encryption keys:

| Direction | Salt | Info |
| --------- | ---- | ---- |
| Output    | DataStream-Salt*X* | DataStream-Output-Encryption-Key |
| Input     | DataStream-Salt*X* | DataStream-Input-Encryption-Key |

Where *X* is `seed` (64 bit) from the response to `SETUP`. It shall always be
treated as an unsigned integer (`%llu`), so `-3431997079003895594` would be
`15014746994705656022`. The salt value in this case would then be
`DataStream-Salt15014746994705656022`.

#### Message format

The format of the data sent on the data channel is still unclear, so this is mostly
educated guesses. Each message includes a 32 byte header where the first four bytes are
the message size. Messages can be segmented over several packets, so it's necessary to
put data in a buffer and decode from that. The message format looks like this:

| Field | Size | Comment |
| ----- | ---- | ------- |
| Size | 4 byte | Size of message, including size field and all other headers
| Message Type | 12 byte | Either `sync` for a request or `rply` for a response. Remaining bytes are padded with zeroes (binary, not the digit 0). Might be padding or other unused fields(?).
| Command | 4 byte | Only `comm` and `cmnd` seen so far. If *Message Type* is `rply`, this field is zero.
| Sequence number | 8 byte | This is either one or two individual fields, it's not entirely clear. A `rply` message will always contain the same value here as it's corresponding `sync` message. If *Command* is `comm`, then the value is always the same for all requests. Upper four bytes seems to be 1 and the lower four bytes random (generated at session start). If *Command* is `cmnd`, then each request has a random value.
| Padding | 4 byte | Seems to always be zeroes, maybe has other purpose?
| Payload | *Size* - 32 | Any payload included in the message, always a binary plist(?).

Some real world examples should make it more clear. Here is one without payload:

```raw
size=32  sync                     cmnd     sequence number   padding
00000020 73796e630000000000000000 636d6e64 cf493446 9b4941ae 00000000

size=32  rply                              sequence number   padding
00000020 72706c790000000000000000 00000000 cf493446 9b4941ae 00000000
```

And here's one with payload:

```raw
size=157 sync                     comm     sequence number   padding   payload
0000009d 73796e630000000000000000 636f6d6d 00000001 6155c3e0 00000000   62706c6973743030d1010256706172616d73d1030454646174614f103b3a08102000aa010c080110001801200028013000aa052436423031354543352d313941412d344534412d394345442d304439343742383144393635080b12151a0000000000000101000000000000000500000000000000000000000000000058

size=74  sync                              sequence number   padding   payload
0000004a 72706c790000000000000000 00000000 00000001 6155c3e0 00000000   62706c6973743030d0080000000000000101000000000000000100000000000000000000000000000009
```

If payload is included with a message, it's serialized as a binary property list and has
this format (others might exist, but have not been seen yet):

```javascript
{"params": {"data": xxx}}
```

Where `xxx` is one or more transported messages. Each message is prepended with the message
size encoded as a [varint](https://developers.google.com/protocol-buffers/docs/encoding#varints), 

One example looks like this:

```javascript
{'params': {'data': b'0\x08& \x00\xd2\x02\x02\x08\x02\xaa\x05$E66952D1-F8F3-4F58-8914-4B507443B321'}}
```

The first byte (in this case), `0x30` decodes to 48 which happens to be the size of
the remaining data. Decoding that data as a protobuf message yields:

```raw
type: SET_CONNECTION_STATE_MESSAGE
errorCode: NoError
[setConnectionStateMessage] {
  state: Connected
}
uniqueIdentifier: "E66952D1-F8F3-4F58-8914-4B507443B321"
```

#### General message flow

From here on, protobuf messages are exchanged in a similar manner to how
the MRP protocol works. They are encapsulated as previously described. One
thing to note is that the sender sets *Command* to `comm`. The receiver on
the other hand sets *Command* to `cmnd`. The reason or importance of this
is not yet known.

As an example, here is the initial `DEVICE_INFO_MESSAGE` message sent by
the sender and the answer:

**Sender -> Receiver:**
```raw
Hex:
000001ae73796e630000000000000000
636f6d6d000000016155c3e000000000
62706c6973743030d101025670617261
6d73d1030454646174614f110146c402
080f122430433236323835302d463145
382d344637462d383844462d33463331
39324231413031392000a201ef010a24
39334543443531352d453735422d3442
32332d394237312d3845453730384134
32423132120e50696572726573206950
686f6e651a066950686f6e6522053138
4738322a16636f6d2e6170706c652e6d
6564696172656d6f7465643801406c48
015001620f636f6d2e6170706c652e4d
7573696368017001880103a201116161
3a62623a63633a64643a65653a6666a8
0101b00101c00101e80101f00100fa01
12636f6d2e6170706c652e706f646361
73747382022439444244433031352d32
3038342d343930352d394139442d3234
34333544314345363137a80200b00201
ba020a6950686f6e6531302c36aa0524
30334246453834342d353037412d3430
45382d383938362d3633464446383237
393130330008000b00120015001a0000
00000000020100000000000000050000
0000000000000000000000000164

Binary:
\x00\x00\x01\xaesync\x00\x00\x00\x00\x00\x00\x00\x00comm\x00\x00\x00\x01aU\xc3\xe0\x00\x00\x00\x00bplist00\xd1\x01\x02Vparams\xd1\x03\x04TdataO\x11\x01F\xc4\x02\x08\x0f\x12$0C262850-F1E8-4F7F-88DF-3F3192B1A019 \x00\xa2\x01\xef\x01\n$93ECD515-E75B-4B23-9B71-8EE708A42B12\x12\x0ePierres iPhone\x1a\x06iPhone"\x0518G82*\x16com.apple.mediaremoted8\x01@lH\x01P\x01b\x0fcom.apple.Musich\x01p\x01\x88\x01\x03\xa2\x01\x11aa:bb:cc:dd:ee:ff\xa8\x01\x01\xb0\x01\x01\xc0\x01\x01\xe8\x01\x01\xf0\x01\x00\xfa\x01\x12com.apple.podcasts\x82\x02$9DBDC015-2084-4905-9A9D-24435D1CE617\xa8\x02\x00\xb0\x02\x01\xba\x02\niPhone10,6\xaa\x05$03BFE844-507A-40E8-8986-63FDF8279103\x00\x08\x00\x0b\x00\x12\x00\x15\x00\x1a\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01d
```

Which decodes to:

```raw
type: DEVICE_INFO_MESSAGE
identifier: "0C262850-F1E8-4F7F-88DF-3F3192B1A019"
errorCode: NoError
[deviceInfoMessage] {
  uniqueIdentifier: "93ECD515-E75B-4B23-9B71-8EE708A42B12"
  name: "Pierres iPhone"
  localizedModelName: "iPhone"
  systemBuildVersion: "18G82"
  applicationBundleIdentifier: "com.apple.mediaremoted"
  protocolVersion: 1
  lastSupportedMessageType: 108
  supportsSystemPairing: true
  allowsPairing: true
  systemMediaApplication: "com.apple.Music"
  supportsACL: true
  supportsSharedQueue: true
  sharedQueueVersion: 3
  managedConfigDeviceID: "aa:bb:cc:dd:ee:ff"
  deviceClass: iPhone
  logicalDeviceCount: 1
  isProxyGroupPlayer: true
  isGroupLeader: true
  isAirplayActive: false
  systemPodcastApplication: "com.apple.podcasts"
  enderDefaultGroupUID: "9DBDC015-2084-4905-9A9D-24435D1CE617"
  clusterType: 0
  isClusterAware: true
  modelID: "iPhone10,6"
}
uniqueIdentifier: "03BFE844-507A-40E8-8986-63FDF8279103"
```

**Receiver -> Sender:**
```raw
Hex:
0000004a72706c790000000000000000
00000000000000016155c3e000000000
62706c6973743030d008000000000000
01010000000000000001000000000000
00000000000000000009

Bytes:
\x00\x00\x00Jrply\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01aU\xc3\xe0\x00\x00\x00\x00bplist00\xd0\x08\x00\x00\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t
```

Which decodes to an empty dict (`{}`).

It is important to include `uniqueIdentifier` in the "envelope message" (`ProtocolMessage`) as
the device doesn't seem to respond otherwise. It shall be set to a random UUID4 string.
