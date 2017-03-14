.. _aiohttp-protocol:

Protocol
========

The Apple TV uses the proprietary DAAP protocol, initially created by Apple for
sharing music with iTunes. It is built on top of the DMAP protocol, which uses
HTTP for transport on TCP port 3689. There are already a bunch of sites and
libraries describing and implementing these protocol, please see the reference
list below. This page will concentrate on the technical aspects used to
implement DAAP and DMAP in pyatv.

DAAP and DMAP
-------------
DMAP is basically a HTTP server that responds to specific commands and streams
events back to the client. Data is requested using GET and POST with special
URLs. Data in the responses is usually in a specic binary format, but depending on
the request it can also be something else (like a PNG file for artwork). The
binary protocol will be explained first, as that makes it easier to understand
the requests.

DMAP Binary Format
^^^^^^^^^^^^^^^^^^
The binary format is basically TLV data where the tag is a 4 byte ASCII-string,
the length is a four byte unsigned integer and the data is, well, data. Type
and meaning of a specific TLV is derived from the tag. So we must know which
tags are used, how large they are and what they mean. Please note that Length
is length of the data, so key and length are not included in this size.

A TLV looks like this:

  +---------------+------------------+--------------------+
  | Key (4 bytes) | Length (4 bytes) | Data (Length bytes |
  +---------------+------------------+--------------------+

Multiple TLVs are usually embedded in one DMAP data stream and TLVs may also
be nested, to form a tree:

.. code::

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

All tags currently known by ``pyatv`` is defined in
:py:mod:`pyatv.tag_definitions`.

Decoding Example
^^^^^^^^^^^^^^^^

Lets assume that we know the following three keys:

+------+-----------+---------------------+
| Key  | Type      | Meaning             |
+======+===========+=====================+
| cmst | Container | dmcp.playstatus     |
+------+-----------+---------------------+
| mstt | uint32    | dmap.status         |
+------+-----------+---------------------+
| cmsr | uint32    | dmcp.serverrevision |
+------+-----------+---------------------+

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

.. code::

  + cmst:
    |
    +- mstt: 200
    |
    +- cmsr: 25

Note that *mstt* and *cmsr* are part of the *cmst* container. This is a typical
response that the Apple TV responds with when doing a "playstatusupdate" request
and nothing is currently playing. Other keys and values are included when
you for instance are playing video or music.

Request URLs
^^^^^^^^^^^^
Since DAAP is sent over HTTP, requests can be made with any HTTP client. However,
some special headers must be included. These have been extracted with Wireshark
when using the Remote app on an iPhone and covers ``GET``-requests:

+-------------------------------+----------------------------------------------+
| Header                        | Value                                        |
+===============================+==============================================+
| Accept                        | */*                                          |
+-------------------------------+----------------------------------------------+
| Accept-Encoding               | gzip                                         |
+-------------------------------+----------------------------------------------+
| Client-DAAP-Version           | 3.12                                         |
+-------------------------------+----------------------------------------------+
| Client-ATV-Sharing-Version    | 1.2                                          |
+-------------------------------+----------------------------------------------+
| Client-iTunes-Sharing-Version | 3.10                                         |
+-------------------------------+----------------------------------------------+
| User-Agent                    | TVRemote/186 CFNetwork/808.1.4 Darwin/16.1.0 |
+-------------------------------+----------------------------------------------+
| Viewer-Only-Client            | 1                                            |
+-------------------------------+----------------------------------------------+

For ``POST``-request, the following header must be present as well:

+--------------+-----------------------------------+
| Header       | Value                             |
+==============+===================================+
| Content-Type | application/x-www-form-urlencoded |
+--------------+-----------------------------------+

There are a lot of different requests that can be sent and this library
implements far from all of them. Fact is that there is support for things that
aren't implemented by the native Remote app, like scrubbing (changing absolute
position in the stream). Since it's the same commands as used by iTunes, we can
probably assume that it's the same software implementation used in both
products. Enough on that matter... All the requests that are used by this
library is described in its own chapter a bit further down.

Authentication
^^^^^^^^^^^^^^
Some commands can be queried freely by anyone on the same network as the Apple TV,
like the server-info command. But most commands require a "session id". The
session id is obtained by doing login and extracting the ``mlid`` key. Session id
is then included in all requests, e.g.

  ctrl-int/1/playstatusupdate?session-id=<session id>&revision-number=0

The device will respond with an error (503?) if the authentication fails.

Supported Requests
------------------
This list is only covers the requests performed by ``pyatv`` and is thus not
complete.

.. note::

    This chapter is far from complete. Only an outline is included here.
    Better examples and descriptions will be added when needed.

server-info
^^^^^^^^^^^
**Type:** GET

**URL:** server-info

**Authentication:** None

Returns various information about a device. Here is an example: ::

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

login
^^^^^
**Type:** GET

**URL:** login?hsgid=<hsgid>&hasFP=1

**URL:** login?pairing-guid=<PAIRING GUID>&hasFP=1

**Authentication:** HSGID or PAIRING GUID

Used to login and get a ``session id``, that is needed for most commands.
Example response from device: ::

    mlog: [container, dmap.loginresponse]
      mstt: 200 [uint, dmap.status]
      mlid: 1739004399 [uint, dmap.sessionid]

Expected format for HSGID and PAIRING GUID respectively:

* HSGID: ``XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX``
* PAIRING GUID: ``0xXXXXXXXXXXXXXXXX``

Where ``X`` corresponds to a hex digit (0-F).

playstatusupdate
^^^^^^^^^^^^^^^^
**Type:** GET

**URL:** ctrl-int/1/playstatusupdate?session-id=<session id>&revision-number=<revision number>

**Authentication:** Session ID

The response contains information about what is currently playing. Example
response: ::

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

The field ``cmsr`` (dmcp.serverrevision) is used to realize "push updates".
By setting ``<revision number>`` to this number, the GET-request will block
until something happens on the device. This number will increase for each
update, so the next time it will be 160, 161, and so on. Using revision
number 0 will never block and can be used to poll current playstatus.

nowplayingartwork
^^^^^^^^^^^^^^^^^
**Type:** GET

**URL:** ctrl-int/1/nowplayingartwork?mw=1024&mh=576&session-id=<session id>

**Authentication:** Session ID

Returns a PNG image for what is currently playing, like a poster or album art.
If not present, an empty response is returned. Width and height of image can be
altered with ``mw`` and ``mh``, but will be ignored if available image is smaller
then the requested size.

.. note::

    This request is relatively expensive to perform, so perform it as seldom as
    possible.

ctrl-int
^^^^^^^^
**Type:** POST

**URL:** ctrl-int/1/<command>?session-id=<session id>&prompt-id=0

**Authentication:** Session ID

<command> corresponds to the command to execute. Can be any of ``play``, ``pause``,
``nextitem`` or ``previtem``.

controlpromptentry
^^^^^^^^^^^^^^^^^^
**Type:** POST

**URL:** ctrl-int/1/controlpromptentry?session-id=<session id>&prompt-id=0

**Authentication:** Session ID

Used to trigger various buttons, like menu or select. Must contain the
following binary DMAP data:

.. code:: python

    cmbe: <command> [string]
    cmcc: 0 [string]

No external container is used. <command> can be either ``select``, ``menu`` or
``topmenu``.

setproperty
^^^^^^^^^^^
**Type:** POST:

**URL:** ctrl-int/1/setproperty?<key>=<value>&session-id=<session id>&prompt-id=0

**Authentication:** Session ID

Changes a property for something.

Summary of supported properties:

+-----------------------+------+-------------------------------------+
| Key                   | Type | Value                               |
+=======================+======+=====================================+
| dacp.playingtime      | uint | Time in seconds                     |
+-----------------------+------+-------------------------------------+
| dacp.shufflestate     | bool | Shuffle state on/off                |
+-----------------------+------+-------------------------------------+
| dacp.repeatstate      | uint | Repeat mode (0=Off, 1=Track, 2=All) |
+-----------------------+------+-------------------------------------+

References
----------
Https://en.wikipedia.org/wiki/Digital_Media_Access_Protocol

https://github.com/benumc/Apple-TV-Basic-IP/blob/master/apple_apple%20tv%20(ip).xml

https://nto.github.io/AirPlay.html

http://stackoverflow.com/questions/35355807/has-anyone-reversed-engineered-the-protocol-used-by-apples-ios-remote-app-for-c
