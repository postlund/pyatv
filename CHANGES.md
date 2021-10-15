# CHANGES

## 0.9.5 Oscar (2021-10-15)

The releases are pouring down right now! Two more bug fixes to smoothen the experience:

* Fix relay bug which could result in methods being reported as unsupported
* Add some missing DMAP tags (removes warnings)

**Changes:**

*Protocol: DMAP:*

```
436ba7b dmap: Add missing tags aelb and casa
```

*Other:*

```
5170edd core: Fix relayer fallback bug
```

**All changes:**

```
436ba7b dmap: Add missing tags aelb and casa
5170edd core: Fix relayer fallback bug
```

## 0.9.4 Nightmare (2021-10-15)

This release just contains two minor bug fixes:

* Removal of need for `mypy_extensions` which was never added as an explicit dependency
  but was required in the previous release
* Support for the UID type in OPACK used by Companion, which caused an exception when
  pairing (Companion) for some people

**Changes:**

*Protocol: Companion:*

```
f99bad0 companion: Add support for UID in OPACK
```

*Other:*

```
954f3dd core: Remove need for mypy_extensions
```

**All changes:**

```
f99bad0 companion: Add support for UID in OPACK
0cf4055 docs: Hide internal DeviceInfo.RAW_MODEL
954f3dd core: Remove need for mypy_extensions
41ff2c8 build(deps): bump types-protobuf from 3.17.4 to 3.18.0
8c9f2d9 build(deps): bump deepdiff from 5.5.0 to 5.6.0
```

## 0.9.3 Moondrop (2021-10-12)

Time for another drop with a few fixes and enhancements:

* Official support for python 3.10
* The MRP service is now ignored for tvOS 15 devices
* osvers is handled properly in AirPlay which previously caused an
  exception when connecting to Apple TV 3 (or older) devices
* Stop is now supported in RAOP

No biggies this time, but should make for a smoooother experience!

**Changes:**

*Protocol: MRP:*

```
89c9f2f mrp: Ignore service during scan for tvOS >= 15
```

*Protocol: AirPlay:*

```
5a1f482 airplay: Quiet log of remote control setup failure
a069208 airplay: Handle semver version in osvers
```

*Protocol: RAOP:*

```
5781665 raop: Add support for stop
0ef3232 raop: Report correct progress values
```

*Other:*

```
2d16f1d gha: Run tests on python 3.10
62c29a1 docs: Add docs for app_list and launch_app
```


**All changes:**

```
5781665 raop: Add support for stop
107a692 facade: Support takeover for PushUpdater
536f241 cq: Remove stream.py
2afdad8 relayer: Fix main_instance and add instances
b6165b0 core: Pass takeover method to protocols
99ed67d facade: Support for protocol takeover
9f93f0e core: Add takeover support to relayer
836aa62 docs: Add tvOS 15 to README description
16c22f0 build(deps): bump flake8 from 4.0.0 to 4.0.1
255c96b build(deps): bump pytest-timeout from 2.0.0 to 2.0.1
b881c32 build(deps): bump pytest-timeout from 1.4.2 to 2.0.0
dd38f63 build(deps): bump flake8 from 3.9.2 to 4.0.0
2d16f1d gha: Run tests on python 3.10
0ef3232 raop: Report correct progress values
5a1f482 airplay: Quiet log of remote control setup failure
4f7fe97 core: Don't connect to dummy services
67ae1b8 build(deps): bump pytest-cov from 2.12.1 to 3.0.0
62c29a1 docs: Add docs for app_list and launch_app
89c9f2f mrp: Ignore service during scan for tvOS >= 15
a069208 airplay: Handle semver version in osvers
65b40bd build(deps): bump mediafile from 0.8.0 to 0.8.1
```

## 0.9.2 Lefty (2021-09-27)

What? Another release? Already? Suure... So, I am integrating pyatv 0.9.x with
Home Assistant and I find these small annoyances or missing pieces along the way,
fixing them one by one as I go. This release is thus a micro-update, but it
contains a few nuggets.

A `Music` device model has been added that represents the Music app/iTunes. In
the same department I've added a property called `raw_model` to `DeviceInfo`,
returning a raw model string in case it's not a model known by pyatv. This is
very useful for AirPlay receivers as `raw_model` will usually contain the device
manufacturer and hardware model.

It is now possible to pass a set of identifiers to `pyatv.scan`. The intended
use case is to pass all identifiers belonging to a device to handle cases where a
service is missing or getting deprecated (like MRP).

Making this release from my phone. In bed. So I will stop there and go to sleep...

**Changes:**

*Protocol: DMAP:*

```
180acab dmap: Avoid unnecessary creation of Zeroconf
2e32274 dmap: Add device model Music for Music/iTunes
```

*Protocol: MRP:*

```
7a8b86a mrp: Updates to volume management
```

*Protocol: Companion:*

```
b28a01e companion: Improve pairing requirement detection
```

*Other:*

```
ce90dd6 core: Add raw_model to DeviceInfo
e063ffb scan: Support scanning for multiple identifiers
```

**All changes:**

```
22bf5f2 companion: Enable test that should be enabled
180acab dmap: Avoid unnecessary creation of Zeroconf
ce90dd6 core: Add raw_model to DeviceInfo
2e32274 dmap: Add device model Music for Music/iTunes
3623287 fix wrong param
b28a01e companion: Improve pairing requirement detection
e063ffb scan: Support scanning for multiple identifiers
7a8b86a mrp: Updates to volume management
```

## 0.9.1 Lolbit (2021-09-23)

Minor bug fix release coming up! Should fix connection issues when a stale
MRP service is present after upgrading to tvOS 15. Also improves pairing requirement
handling for AirPlay and RAOP in case access control is set to "Only devices in
my home" (will now report as Disabled). Companion is also reported as Unsupported
for HomePods as pyatv cannot pair with them.

A new convert method to convert a `DeviceModel` to string has been added.

**Changes:**

*Protocol: AirPlay:*

```
2558a89 airplay: Support Disabled pairing requirement
```

*Protocol: Companion:*

```
6cb7269 companion: Better support for pairing requirement
```

*Protocol: RAOP:*

```
d257378 raop: Support Disabled pairing requirement
```

*Other:*

```
70b4992 convert: Add model_str method
535b56b core: Use connect order based on protocol
```

**All changes:**

```
6cb7269 companion: Better support for pairing requirement
d257378 raop: Support Disabled pairing requirement
2558a89 airplay: Support Disabled pairing requirement
70b4992 convert: Add model_str method
535b56b core: Use connect order based on protocol
```

## 0.9.0 JayJay (2021-09-22)

So, what's new? Yeah, right, tvOS 15 was released the day before yesterday
which broke everything. My intention was to release 0.9.0 before tvOS 15
dropped, but things kept popping up and I had no choice but to delay. So here
we are.

The biggest feature in this release is obviously support for tvOS 15. Perhaps
not the most exciting feature per se, but important as most of the
functionality in pyatv is lost without it. The gist is that Apple decided to
drop support for the MRP protocol introduced in tvOS. In practice they didn't
get rid or it, they just allocated a special stream type in AirPlay (2) and
decided to tunnel MRP over it. So MRP is still there, it's just carried over
AirPlay now. As far as I know, this is how they have done it the last couple of
iOS/tvOS releases. So it's not really new, just something no one looked into.
The deprecation of the "regular" MRP protocol is reasonable (who uses the
Remote app nowadays?), so I don't blame Apple for it. Would have been nice to
have figured this out earlier though, as it required a lot of intense reverse
engineering to unravel everything. Now it does work though, so totally worth
it! I have tried to document how it works on the protocols page:

https://pyatv.dev/documentation/protocols/

All needed to get things working again is to provide AirPlay credentials. One
important thing to note though is that you need to re-pair with this release
(or later) to get new credentials. The old ones will only work with `play_url`,
not for tunneling MRP over AirPlay. A small bonus here is that the HomePod
works in the same way as the Apple TV in this regards, so pyatv can now be used
to control HomdPods as well. No pairing is needed for that, it's just
plug-and-play!

Let's leave MRP now... My vision for pyatv is to create a "core", where
protocols work as plugins to provide functionality. The API used by developers
is supposed be towards core and not the protocols themselves. This basically
means that all functions in the API should behave in the same way, no matter
what protocols are used in regards to arguments, return values, listener
interfaces, error handling and so on. This release contains a lof of work
towards realizing that vision. I'm not quite there yet, but it's closer than
ever. Hopefully, this will only manifest itself through more consistent
behavior and not much you as a developer need to pay any attention to. But if
you notice any changes in behavior, this might be the reason. Be sure to report
anything that you find peculiar, it might need fixing or an explanation.

Another minor new feature is that the Audio interface has been extended to
include volume_up and volume_down, which also means those methods are
deprecated in `RemoteControl`. Please update your code for this. Also, all the
protocol specic service types, e.g. `conf.MrpService` and `conf.AirPlayService`
have been deprecated in favor of `conf.ManualService`. Update your code for
this as well, in case you rely on any of them. They will stick around for a few
releases, so your code won't break because of this. The last minor feature is a
helper method called `helpers.is_streamable`, which can check if file is
supported by `Stream.stream_file`.

One last thing... This release fills a big gap that has been present for a long
time: when do you need to pair? Each service now contains a "pairing" property
that will tell you of pairing is needed or not. This makes it possible to
programmatically determine if the pairing procedure needs to to performed,
something that wasn't clear before. After scanning, just iterate all services
and pair the ones requiring it. A similar property has been added for passwords
as well, called `requires_password`. If True, then a password is required to
connect. Only applicable to RAOP so far (it works for AirPlay as well, but
there's no support for passwords in AirPlay yet).

To round things up, I just wanted to say that docker images are automatically
built for new releases as well as the latest commit on master, making it easy
to test pyatv without having to install any additional software other than
docker. I still have some areas to improve, but it's a good start. This release
will be the first release having docker images pre-built as it's tricky to
backport.

That is it for now. Make sure to check out the migration guide to get some
hints on what you need to do when upgrading.

Be sure to check out the migration notes before upgrading:

https://pyatv.dev/support/migration/

**Notes:**

* mediafile replaced audio-metadata as a dependency in this release
* At least version 3.17.3 of protobuf is required

**Changes:**

*Protocol: DMAP:*

```
099c975 dmap: Add support for pairing requirement
```

*Protocol: MRP:*

```
6177e86 mrp: Add support for pairing requirement
0bdd614 mrp: Add support for Audio interface
2495e56 mrp: Extract build number from DEVICE_INFO
```

*Protocol: AirPlay:*

```
31bf148 airplay: Add support for pairing requirement
af5c441 airplay: Add support for requires_password
8c35d1f airplay: Add support for transient pairing
a407efa airplay: Support MRP tunneling over AirPlay 2
```

*Protocol: Companion:*

```
e49b9ef companion: Add support for pairing requirement
```

*Protocol: RAOP:*

```
d47924d raop: Send empty audio during latency period
f075d4d raop: Add support for pairing requirement
f66563a raop: Add support for requires_password
```

*Other:*

```
9339954 if: Add volume_up and volume_down to Audio
1c11600 gh: Convert issue templates to forms
8f7f9bd gha: Build and publish Docker containers
4f76bf3 core: Switch from audio-metadata to mediafile
33a0d5d deps: Bump protobuf to 3.17.3
14a35fe helpers: Add is_streamable method
21dec3e facade: Close connections only once
09bd203 facade: Close protocols on device update
f5f84b1 facade: Return remaining tasks in close
```

**All changes:**

```
c04e1a5 build(deps): bump pytest-xdist from 2.3.0 to 2.4.0
d47924d raop: Send empty audio during latency period
8ecf4b5 http: Handle responses when no receiver exists
45a4385 build(deps): bump pylint from 2.10.2 to 2.11.1
07804a0 build(deps): bump mypy-protobuf from 2.9 to 2.10
52cbe4c build(deps-dev): bump tox from 3.24.3 to 3.24.4
884edb1 build(deps): bump black from 21.8b0 to 21.9b0
5b0984c docs: Update scan, pair and connect docs
f075d4d raop: Add support for pairing requirement
6318fee airplay: Refactor pairing requirement extraction
31bf148 airplay: Add support for pairing requirement
099c975 dmap: Add support for pairing requirement
b57b2bb dmap: Add support for pairing requirement
e49b9ef companion: Add support for pairing requirement
6177e86 mrp: Add support for pairing requirement
af5c441 airplay: Add support for requires_password
f66563a raop: Add support for requires_password
8049c82 if: Add protocol specific methods for service info
c07cb1c if: Restructure service handling
3cdb1fb core: Move state_producer to support
9aeec0a core: Move state_producer to support
2f84917 core: Move back device_info to support
da765a3 if: Rely solely on BaseService internally
b3221a5 conf: Extract BaseConfig interface
88c66bc docs: Minor updates
d4163a7 facade: Verify support in play_url
0ed417e airplay: Base play_url availability on properties
9339954 if: Add volume_up and volume_down to Audio
f563eea env: Add work to .gitgnore
0bdd614 mrp: Add support for Audio interface
dc247bd mrp: Update some MRP protobuf messages
7dc7c99 gha: Add workflow_dispatch: to tests workflow
c7cf760 docs: Various minor updates
52210b5 if: Keep position within limits
671c24a core: Move scan to core
78386f6 core: Move facade to core
3cba1c4 core: Move net to core
0227e06 core: Move mdns to core
743988a core: Move facade to core
9812b0e core: Move device_info to core
e53a6c1 core: Move protocol details to protocols module
63b1d09 core: Move raop to protocols
b0a780e mrp: Move mrp to protocols
6f8c90b core: Move dmap to protocols
9196a88 core: Move companion to protocols
b0758a9 core: Move airplay to protocols
8ee902b gh: Fix bad labels for investigation and bugs
3e01c2e gha: Change tags and labels a bit for containers
1c11600 gh: Convert issue templates to forms
c126d77 gha: Fix remaining issues with release workflow
826bb58 gha: Fix building containers and make releases
8f7f9bd gha: Build and publish Docker containers
2495e56 mrp: Extract build number from DEVICE_INFO
a548587 conf: Move device_info implementations to protocol
c6bb384 support: Add collection method dict_merge
8fcca30 devinfo: Add new tvOS build numbers
bac81ef if: Base DeviceInfo on dict
f66aa84 raop: Add support for legacy pairing
7e1ca68 core: Refactor pair to take service
d974f08 core: Set up protocols independently
a46c068 docs: Add instructions for close
4a24ac9 airplay: Various connection robustness changes
5a6c267 mrp: Add VolumeDidChangeMessage
8c35d1f airplay: Add support for transient pairing
61ef4e2 core: Return protocol when setting up protocol
a407efa airplay: Support MRP tunneling over AirPlay 2
e060b9e mrp: Generalize set up of MRP
8a88129 docs: Remove internal things from API docs
5f1a55e core: Allow setup to yield multiple instances
384a7a6 mrp: Add new protobuf messages
0b0648e support: Add length field to packet
ae5785b raop: Move packets to support
6bc3cf1 raop: Move metadata to support
402ae73 raop: Move RTSP implementation to support
eb71a3d auth: Add abstract class for HAP channels
d7f6394 raop: Generalize the RTSP implementation
1da0414 auth: Refactor HAP for generic key derivation
e04736c airplay: Pick most suitable pairing type
7c667b9 airplay: Add module to parse features
e582644 auth: Add HAPSession used for encryption
b328826 airplay: Add helper verify_connection to auth
9f81aa9 http: Add pre/post processors to HttpConnection
a2d0218 airplay: Add HAP auth support
044aa1d airplay: Add auth type to pair_setup
7b9dda8 airplay: Generate new credentials for Pair-Setup
bcdf21b airplay: Refactor auth for multiple types
9783fea airplay: Add legacy to auth procedure name
ee6437a auth: Move tlv8 and srp to auth modules
68ea864 auth: Refactor to general HAP pairing scheme
eac1428 airplay: Rename auth to auth_legacy
4f76bf3 core: Switch from audio-metadata to mediafile
33a0d5d deps: Bump protobuf to 3.17.3
bca490e build(deps): bump mypy-protobuf from 2.5 to 2.9
c8e22b6 build(deps): bump pytest from 6.2.4 to 6.2.5
ae05921 build(deps): bump black from 21.7b0 to 21.8b0
001d920 scripts: Add support for year, track and genre
14a35fe helpers: Add is_streamable method
81739c8 conf: Add password to RAOP output
c5513b3 docs: Use absolute address to logo in README
415c8a5 build(deps): bump pdoc3 from 0.9.2 to 0.10.0
5900c29 build(deps): bump pylint from 2.9.6 to 2.10.2
46507f3 facade: Return pending tasks from previous close
21dec3e facade: Close connections only once
09bd203 facade: Close protocols on device update
83dfe6b core: Add state_was_updated to StateProducer
dd15ef9 facade: Only propagate one device update
9602344 if: Move StateProducer to core and add max_calls
6a498d7 build(deps): bump pylint from 2.9.6 to 2.10.2
f5f84b1 facade: Return remaining tasks in close
b2333d2 docs: Make some clarifications for AirPlay remote
b2d2b1b build(deps-dev): bump tox from 3.24.0 to 3.24.1
94f3b88 docs: Fix broken diagram in AP 2
5c036e9 docs: Add remote control docs for AirPlay 2
1877f65 build(deps): bump codecov from 2.1.11 to 2.1.12
e1b5687 build(deps): bump isort from 5.9.2 to 5.9.3
a9675fd Fix spelling error
454dcff docs: Add issue regarding cellcomtvappleos
e36602e docs: Add entry for Illegal instruction
415ee61 Disable pylint instead of mypy
075ac89 mrp: Disable some type checking
1630419 docs: Fix broken links in supported_features
bbdd88b build(deps): bump pylint from 2.9.5 to 2.9.6
```

## 0.8.2 Helpy (2021-07-28)

Time for another minor release! Highlights this time is
improved scanning, password protected RAOP services, support
for HSCP and some remote buttons in Companion.

An issue hwere some devices were not discovered by Home Assistant
anymore suddenly appeared (pun intended). Some digging concluded
that asking for too many Zeroconf services in one request might
yield a response too big to fit in one IP packet. This makes the
sender silently drop records, rendering the response incomplete
without pyatv knowing that. Since Companion and RAOP was added in
0.8.0 (which require three new services in total), that was the
tipping point. From now on, pyatv will spread services over a few
requests to work around this issue.

It is now possible to stream audio to password protected AirPlay
receivers thanks to @Schlaubischlump! A password can be passed
to atvremote via `--raop-password` and it's explained how to do
it programmatically in the documentation.

HSCP (unsure what it stands for, maybe something like
*Home Sharing Control Protocol*?) is used to control instances of
iTunes or Music running on a Mac. Unfortunately, Apple decided
to require FairPlay authentication in macOS 11.4, so this will
only work if you are running an OS with lower version number than
that.

Some buttons in the remote control interface is now supported by
the Companion protocol. The API reference on
[pyatv.dev](https://pyatv.dev) actually lists which which protocols
implement a certain feature now, so it's recommended to look there
for current status.

There are a few house-keeping fixes in this release as well,
mostly related to tests, documentation and environment. A complete
list is below. See you all next time!

**Changes:**

*Protocol: DMAP:*

```
271c319 dmap: Add support for HSCP service
```

*Protocol: Companion:*

```
af77f3e companion: Add support for several buttons
bdaf12a companion: Generalize OPACK error handling
```

*Protocol: RAOP:*

```
42a0e58 Add support for password protected RAOP devices
```

*Other:*
```

8faa4eb core: Fix potential aiohttp client session leak
9be93f1 scan: Support scanning for specific protocols
4d7f5bf debug: Include zeroconf properties in debug log
2cf35e3 gha: Another attempt to re-run tox on failure
3b55c6a env: Update metadata in setup.py
```

**All changes:**

```
4c25021 mdns: Verify end condition with all services
8fd7e09 mdns: Cache parsed services
534006d mdns: Split multicast request in multiple messages
bd6cc7c mdns: Ask for sleep-proxy in unicast requests
44506a5 mdns: Split unicast requests over several messages
5ed0491 mdns: Ignore duplicate records in ServiceParser
84ae2c5 mdns: Refactor service parser to a class
4eaadc5 build(deps): bump types-protobuf from 3.17.3 to 3.17.4
af77f3e companion: Add support for several buttons
7579a49 companion: Convert functional tests to pytest
e1dab57 build(deps): bump pylint from 2.9.4 to 2.9.5
1618e13 build(deps): bump pylint from 2.9.3 to 2.9.4
271c319 dmap: Add support for HSCP service
42a0e58 Add support for password protected RAOP devices
bdaf12a companion: Generalize OPACK error handling
536e271 cq: Refactor pairing handlers
242023a build(deps): bump black from 21.6b0 to 21.7b0
0c8b59b build(deps): bump types-protobuf from 3.17.1 to 3.17.3
8faa4eb core: Fix potential aiohttp client session leak
9be93f1 scan: Support scanning for specific protocols
687f3bf mdns: Fix unstable multicast test
e1bc26f env: Only verify docs with py3.8
10a408d build(deps-dev): bump tox from 3.23.1 to 3.24.0
00d3946 build(deps): bump types-protobuf from 3.17.0 to 3.17.1
809c5a3 Update README.md
9afd181 scan: Move scan code to protocols
438e70e build(deps): bump types-protobuf from 0.1.13 to 3.17.0
3b5e7d8 build(deps): bump isort from 5.9.1 to 5.9.2
d1dbc5d build(deps): bump pylint from 2.8.3 to 2.9.3
4d7f5bf debug: Include zeroconf properties in debug log
a147a27 gha: Fix running tox on Windows
0b0908d docs: Add feature name and supported protocols
2cf35e3 gha: Another attempt to re-run tox on failure
f9f00b6 build(deps): bump mypy-protobuf from 2.4 to 2.5
3b55c6a env: Update metadata in setup.py
a8b4d88 gha: Re-run tox without cache if failure
```

## 0.8.1 Glitchtrap (2021-06-24)

This minor release contains a few improvements to the RAOP protocol.
First and foremost, `time.perf_counter` is now used in favor of
`time.monotonic` for audio scheduling. Scheduling has also been changed to work
with "global time" (from stream start) instead of per frame. These changes
improve streaming stability, with less chance of getting out of sync. They were
also necessary to get streaming working on Windows.

Another important addition in the streaming department is the ability to read
input from a FILE-like object, instead of just from a filename. One usecase for
this is to take input via stdin from another process and send it to a receiver.
`atvremote` has been adjusted to read from stdin if `-` is specified as
filename. Here's an example streaming output from ffmpeg (RTSP as input!):

```shell
ffmpeg -i rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov -f mp3 - | atvremote -s 10.0.10.184 --debug stream_file=-
```

Documentation for this:

https://pyatv.dev/documentation/atvremote/#streaming
https://pyatv.dev/development/stream/#stream-a-file

**Changes:**

*Protocol: RAOP:*

```
f41d552 raop: Sync sending based on absolute time
bd15ff2 raop: Use perf_counter instead of monotonic
4abfc94 raop: Add small buffer to BufferedReaderSource
ee1ee94 raop: Fix timing when starting to stream
8096928 raop: Support streaming files from a buffer
```

**All changes:**

```
f41d552 raop: Sync sending based on absolute time
bd15ff2 raop: Use perf_counter instead of monotonic
03f9a6b build(deps): bump mypy from 0.902 to 0.910
244d9ee build(deps): bump isort from 5.8.0 to 5.9.1
a23c144 docs: Add missing tutorial example
4abfc94 raop: Add small buffer to BufferedReaderSource
ee1ee94 raop: Fix timing when starting to stream
8096928 raop: Support streaming files from a buffer
a2df952 docs: Add tutorial as an example
6cf2f4c build(deps): bump types-protobuf from 0.1.12 to 0.1.13
```

## 0.8.0 Freddy (2021-06-17)

Here comes a new release, filled to the brim with new stuff! First and foremost, it
introduces support for not one but *two* new protocols: Companion and RAOP. The
Companion protocol is used to list and launch apps installed on an Apple TV as well
improving power management support. RAOP adds support for proper audio streaming
to AirPlay receivers. Both protocols are still early in development and may contains a
few bugs (yeah...). You will likely see new features added to these over time.

A big new change in this release, that isn't really noticeable at first, is a new layer
that relays calls between public interface methods and underlying protocols. What does
this mean then? Well, we have the public interfaces (Metadata, RemoteControl. etc.)
and the protocols implementing them (DMAP, MRP, RAOP, etc). Prior to this release,
DMAP and MRP would fully implement all of the interfaces (with a minor exception of
Stream) and there was a requirement to configure one of them. From now on however,
there's no such restriction as it's possible to connect to any number of protocols.
The Feature interface tells us what is actually supported. The new layer (internally
called *facade*) will automatically figure out which of the available protocol has the
most appropriate implementation and call that. If two protocols implement the same
interface method, there's mechanisms internally to pick the best one. An example is
the Power interface, where MRP and Companion both provide implementations for `turn_on`
and `turn_off`. If both these protocols are configured, then the implementations
provided by the Companion protocol will be used (as they are better), otherwise
fallback will happen to MRP.

From now on, the change log format changes a bit to list changes per protocol and
scripts. The goal is to make it easier to see what has changed or been fixed. This
release also introduces release names and all releases from now on will get a release
name based on characters from Five Nights Freddy's. First letter of the next release
name follows the letter of the previous one (the next release will be called
Glitchtrap for instance). Oh, and this release text is also new...

Other changes include a *big* overhaul of the documentation. A lot of things have
been improved and added, for instance a new tutorial and a few new examples. There's
a configuration for GitPod, so you can get going with pyatv development with a single
click!

Be sure to check out the migration notes before upgrading:

https://pyatv.dev/support/migration/

There's also a new page with a better summary of supported features:

https://pyatv.dev/documentation/supported_features/

I guess that is it!

**Changes:**

*Protocol: DMAP:*

```
* Reset revision if push update fails (#1004) fixes #1000
```

*Protocol: MRP:*

```
* bug: Do not deep copy protobuf messages (#1105) fixes #1038
* bug: Handle missing artwork gracefully (#1033) fixes #937
* bug: Implement and enforce internal protocol state (#1009) fixes #1007
```

*Protocol: AirPlay:*

```
* General clean up of module but no new features
```

*Protocol: Companion:*

```
* Initial release
* Adds the Apps interface (list and launch apps)
* Implements turn_on and turn_off in the Power interface
```

*Protocol: RAOP:*

```
* Initial release
* Supports streaming WAV, MP3, OGG and Vorbis files
* Reads metadata from supported formats (artist, album and title)
* Supports volume controls
```

*Script: atvlog:*

```
* Exit if no output was generated (#1001)
* Support serving output via web server (#997)
```

*Script: atvremote:*

```
* Fix bugs in manual mode (parameters not respected properly)
```

**Notes:**

* audio-metadata, bitarray and miniaudio are new dependencies in this release
* At least version 3.12.0 of protobuf is required

**All changes:**

```
6ffef9f build(deps): bump pytest-xdist from 2.2.1 to 2.3.0
8e5691c build(deps): bump mypy-protobuf from 1.24 to 2.4
70ef974 docs: Add examples
b91b099 deps: Don't bump bitarray past 2.1.2
1914a04 docs: Clarification regarding device listener
0bc6eae docs: Add a tutorial
5bbb81a docs: Update migration guide for 0.8.0
4d9dbd4 scan: Migrate to use get_unique_id internally
0049db1 scan: Be more forgiving if service parsing fails
ecacad7 tests: Make RAOP work in fake device
c36e6b5 raop: Teardown session after streaming
116d29d build(deps): bump zeroconf from 0.28.0 to 0.28.2
b8c3819 scripts: Unset PIP_USER in setup_dev_env.sh
cd849b7 Upgrade to GitHub-native Dependabot
5f590f5 build(deps): Bump bitarray from 2.1.2 to 2.1.3
aa4b53d raop: Fallback to AirPlay credentials
a5bd14c raop: Only perform auth-setup for AirPort Express
795081b docs: Various documentation updates
6cfa66c helpers: Add get_unique_id
1c3adcf mypy: Fix typing issues
73bb7fa build(deps): Bump mypy from 0.812 to 0.902
85d03f0 build(deps): Update bitarray requirement from <2.1.1,==2.1.0 to ==2.1.2
cc5bc8c raop: Support devices not implementing /info
dae7518 raop: Minor updates to documentation
1b3c183 raop: Handle muted volume level
cf2696e raop: Only allow one stream at the time
eaec0a5 raop: Support set_volume, volume_up, volume_down
462512e raop: Make sure authentication is performed early
3b37ec8 raop: Initial volume support
15e4501 support: Add map_range function
4ed1b2c facade: Enforce percentage level for audio
0dea45f deps: Temporarily lock bitarray <2.1.1
c1acb3b build(deps): Bump black from 21.5b2 to 21.6b0
8e13c3c build(deps): Bump codespell from 2.0.0 to 2.1.0
b844966 raop: Correctly implement position in metadata
1d665d5 raop: Support progress (position and total_time)
fae7b41 cq: Clean up usage of ensure_future
6c0cd54 raop: Fix instability in retransmission test
c2f7287 raop: Send feedback if supported by receiver
58220e5 raop: Avoid blocking I/O when loading metadata
7eb961d raop: Avoid blocking I/O in MiniaudioWrapper
292fbb5 raop: Add initial functional tests
68abbdc audiogen: Add new script to generate audio files
5f3d1a8 raop: Add basic fake device
32f8ed7 http: Add a simple web server implementation
f1bfce3 build(deps): Bump pytest-cov from 2.12.0 to 2.12.1
044f55e build(deps): Bump pylint from 2.8.2 to 2.8.3
eb2d36d build(deps): Bump black from 21.5b1 to 21.5b2
1d2b3a1 env: Don't post comment with GitPod link
2b5b280 http: Ignore type mypy cannot find
18d1597 http: Ignore case in when parsing headers
0bd54d8 airplay: Fix encoding name typo
e65eb59 airplay: Fix patching in tests
74401a0 raop: Use feedback endpoint for keep-alive
428b9b1 raop: Verify using AirPlay if credentials provided
99f3037 airplay: Unify credentials with other protocols AirPlay was the first protocol to introduce SRP and credentials and suffers some internal design flaws that were improved when implementing the other protocols. This change tries to make the AirPlay implementation look more like how it's done in the other protocols using SRP, e.g. MRP. It's a good start, but some additional work needs to be done regarding credentials parsing (but leaving that for the future).
894f0fd hap_srp: Rename Credentials to HapCredentials
2211a00 atvremote: Fix bugs in manual mode
be37e9f net: Move HttpSession to http
46ae307 net: Move aiohttp session management to http
7b62f96 airplay: Move StaticFileWebServer to http
722967e airplay: Simulate streaming from fake device
7aa1e35 airplay: Refactor to use new http module
1ef8684 rtsp: Use composition instead of inheritance
2d2bd57 raop: Convert RTSP to use the new HTTP module
57b3b5b http: Generalize RTSP parsing to HTTP
ded7458 companion: Fix case when app_list fails (#1106)
980454e mrp: Do not deep copy protobuf messages (#1105)
cc3de66 companion: Add support for turn_on and turn_off (#1104)
d08c73a build(deps): Bump miniaudio from 1.43 to 1.44
f57f122 raop: Set correct progress in metadata (#1100)
2dd1539 raop: Support retransmission of lost packets (#1099)
5f5ad5b raop: Add support for AirPort Express (#1098)
311ca61 raop: Raise exception on RTSP error code (#1097)
a24ee74 conf: Add device info for AirPort Express (#1096)
75d31f4 mdns: Ignore link-local addresses when scanning (#1095)
9393b51 build(deps): bump black from 21.5b0 to 21.5b1 (#1065)
3d541bf build(deps): bump pydocstyle from 6.1.0 to 6.1.1
0fd1393 build(deps): bump pylint from 2.7.4 to 2.8.2 (#1044)
da37e28 docs: Update README.md (#1092)
a64ca4d docs: General uplift of documentation (#1091)
8822d66 build(deps): bump pydocstyle from 6.0.0 to 6.1.0
be08cfa raop: Implement Metadata and PushUpdater interface (#1084)
5051a17 build(deps): bump pytest-cov from 2.11.1 to 2.12.0
c1d4d74 raop: Use metadata from input file as metadata (#1080)
dc6c042 if: Add audio interface (#1074)
41b5705 raop: Respect receiver audio properties (#1073)
f2c625f raop: Add initial support for RAOP (#1060)
a93601f facade: Add PushUpdates to the feature interface (#1072)
6f53e7b env: Enable CodeQL (#1070)
54d876a some small additions to the OPACK definitions (#1064)
bb5ac0e build(deps): bump flake8 from 3.9.1 to 3.9.2
0cde7a0 scripts: Protocol clean up (#1057)
35c49b8 build(deps-dev): bump tox from 3.23.0 to 3.23.1
f129725 build(deps): bump black from 21.4b2 to 21.5b0
a01ff9c build(deps): bump pytest from 6.2.3 to 6.2.4
cbfeba6 build(deps): bump deepdiff from 5.3.0 to 5.5.0
c85f211 build(deps): bump black from 21.4b1 to 21.4b2 (#1050)
f15fa67 mrp: Tidy upp keyboard related messages (#1048)
22a0b29 Add series name, season and episode number (#1049)
51a1da3 build(deps): bump black from 21.4b0 to 21.4b1 (#1046)
f344a12 docs: Add section about commands in Companion (#1047)
b5d015f docs: Change "Apps" section to "Known Issues" (#1045)
58f8925 Implement facade pattern for public interface (#1042)
3225c98 companion: Add pairing function tests (#1041)
e230f1d gha: Run tests workflow on master (#1039)
7979b1b build(deps): bump black from 20.8b1 to 21.4b0
f6976e4 script: Install docs dependencies in dev env (#1032)
c68ed51 mrp: Handle missing artwork gracefully (#1033)
5df2295 gha: Minor changes to codecov (#1031)
021cc7a docs: Clarify AAD for encryption in Companion (#1030)
33d504d env: Various updats to environment and GitPod (#1029)
f173531 env: Remove documentation tab from GitPod for now (#1028)
1e8ffdc env: Add GitPod configuration
d2dbc9e cq: Sort imports with isort (#1026)
caeb039 build(deps): bump pytest-asyncio from 0.14.0 to 0.15.1 (#1027)
bb7ff8f Fake device and tests for Companion (#1025)
ddbe170 if: Add Apps interface to Companion (#1022)
8ebc67d knock: Suppress CancelledError exception (#1023)
ea5d3ea Support for the Companion link protocol (#657)
e033942 scripts: Add module to log output (#1017)
235484e build(deps): bump deepdiff from 5.2.3 to 5.3.0
646c6d6 doc: Add mermaid to support diagrams (#1014)
b0c9355 chore: update types in CryptoPairingMessage to be optional (#1013)
9cb96ff mrp: Implement and enforce internal protocol state (fixes #1007) (#1009)
df43f78 build(deps): bump flake8 from 3.9.0 to 3.9.1
6d42bf5 build(deps): bump typed-ast from 1.4.2 to 1.4.3
d6ae8e9 dmap: Reset revision if push update fails (#1004)
ea1f816 build(deps): bump pytest from 6.2.2 to 6.2.3
33acac2 atvlog: Exit if no output was generated (#1001)
c59a3d3 build(deps): bump pylint from 2.7.2 to 2.7.4
f3f7a1a atvlog: Support serving output via web server (#997)
377e0eb build(deps): bump pydocstyle from 5.1.1 to 6.0.0
00fa0cd protobuf: Bump lower version to 3.12.0 (#991)
d291104 build(deps): bump flake8 from 3.8.4 to 3.9.0
```

## 0.7.7 (2021-03-12)

**Changes:**

* Fix bug where apps would appear to crash on tvOS 14.5 (beta)
* Add a retry to heartbeat loop
* Add new script that parses logs: atvlog

**All changes:**

```
60df163 mrp: Use GenericMessage for heartbeats (#975)
8df084f support: Convert knock to use asyncio (#988)
14196da gh: Add example to attach log to a bug report (#984)
dbe734c build(deps-dev): bump tox from 3.22.0 to 3.23.0
1e1922e cq: Run pylint from tox (#979)
7464cb7 atvlog: Rename log2html and bundle it (#982)
34d2f53 log2html: Add separate include and exclude filters (#981)
0a6fa5e log2html: Add generation date and command (#980)
7184717 mrp: Add retry to heartbeats (#978)
b0eaaef log2html: Allow toggling of showing date (#974)
adda918 build(deps): bump mypy from 0.800 to 0.812
fa8b05d gha: Save log for log2html using pygithub (#972)
7584a2c log2html: Fix broken log entry loading (#971)
090ba35 build(deps): bump deepdiff from 5.2.2 to 5.2.3 (#969)
ce3fecd gha: Store issue/comment body as file for log2html (#970)
1ee2691 log2html: Support Home Assistant log format (#967)
b9dcadc log2html: Add text and log level filtering (#966)
49b17f9 log2html: Render log entries with javascript (#965)
5935d50 build(deps-dev): bump tox from 3.21.4 to 3.22.0
aa9b2cf gha: Generate html logs for logs in issues (#962)
aa2aa18 log2html: Support environment variable as input (#961)
dd91239 log2html: New script converting logs to HTML pages (#960)
659031e build(deps): bump pytest-xdist from 2.2.0 to 2.2.1
46aae2f build(deps-dev): bump tox from 3.21.3 to 3.21.4
49aab09 build(deps): bump mypy-protobuf from 1.23 to 1.24
```

## 0.7.6 (2021-01-29)

**Changes:**

* DNS parsing has been re-written which should be more stable
  and handle more use cases
* TCP keep-alive has been added to more platforms, FreeBSD being one of them
* Player management has been totally re-written for MRP, so hopefully
  play state should be more accurate now
* A delay has been added to turn\_off (MRP), so it should work again
* A heartbeat loop has been added that sends a "heartbeat" to the device
  every 30s to detect connection problems
* Protobuf definitions have been further lifted to match later tvOS versions

**Notes:**

* Fixed a bug where Playing instancess were not immutable
* Push updates are only issued when something in the Playing instance changed.
  Previously, unrelated changes to the device could trigger push updates with
  the same content in Playing.

**All changes:**

```
0994733 build(deps-dev): bump tox from 3.21.2 to 3.21.3 (#946)
8e0fc01 mrp: Add some protobuf messages for volume (#947)
5752ae3 mrp: Fix handling of active client (#944)
7e3bcf5 if: Convert Playing to data class (#943)
2b8fb74 build(deps): bump pytest from 6.2.1 to 6.2.2
607d78c build(deps): bump mypy from 0.790 to 0.800
a77c453 build(deps-dev): bump tox from 3.21.1 to 3.21.2
393efbd build(deps): bump pytest-cov from 2.11.0 to 2.11.1
6bb284f build(deps): bump pytest-cov from 2.10.1 to 2.11.0
3c488b2 build(deps): bump deepdiff from 5.2.1 to 5.2.2
cc41f33 mrp: Add support for heartbeats (#925)
aec7362 mrp: Add support for heartbeats (#926)
9af7609 dns: Use UTF-8 for names, and (attempt) to handle dots in names (#927)
b527506 build(deps-dev): bump tox from 3.21.0 to 3.21.1
fdf843f mrp: Support default supported commands (#924)
f0f7eaf mrp: Add delay in turn_off between commands (#923)
df56149 mrp: Add fields to UpdateOutputDevice (#921)
280de0f Do not post duplicate push updates (#920)
f9f7238 build(deps-dev): bump tox from 3.20.1 to 3.21.0
aed9028 mrp: Fix a few playback state edge cases (#916)
e176ce7 mrp: Improve client and player handling (#915)
3ca2b0f support: Add new tvOS versions to list (#913)
ccfa5eb mrp: Major updates to protobuf messages (#912)
3eb9d3a Improve DNS message parsing for mDNS (#899)
c524244 build(deps): bump deepdiff from 5.0.2 to 5.2.1
87a159e build(deps): bump typed-ast from 1.4.1 to 1.4.2
e61fb47 Slightly refine protobuf and srptools base requirements (#902)
b2e80b3 net: Use TCP keepalive on more platforms (#897)
03e4438 build(deps): bump codecov from 2.1.10 to 2.1.11
f3dd0af build(deps): bump pytest from 6.2.0 to 6.2.1
5f3383b build(deps): bump pytest-xdist from 2.1.0 to 2.2.0
5ccb23f build(deps): bump pytest from 6.1.2 to 6.2.0
```

## 0.7.5 (2020-12-08)

**Changes:**

* Revert to use random source port for MDNS
* Fix "Received UpdateClientMessage for unknown player xxx""

**All changes:**

```
cd6d53f mdns: Revert binding to port 5353
a394b52 mrp: Handle UpdateClient before SetState
a3d46d3 build(deps): bump mypy from 0.782 to 0.790
c648eaa update MANIFEST.in, add missing file
162f319 build(deps): bump pytest from 6.1.1 to 6.1.2
f1a7223 build(deps): bump pdoc3 from 0.9.1 to 0.9.2
0b97aab build(deps): bump codespell from 1.17.1 to 2.0.0
795aaa7 Update setup.py, extend exclude mask
5e27bc7 gha: Fix python 3.9 and use env files
```

## 0.7.4 (2020-10-12)

**Changes:**

* PIN code screen for MRP will now disappear after pairing
* Less and more compact debug logs in mdns and knock

**All changes:**

```
9f1d1d0 mrp: Verify credentials after pairing
1d799f2 cq: Minor clean ups and fixes
061add1 build(deps): bump codecov from 2.1.9 to 2.1.10
dc31ac9 build(deps-dev): bump tox from 3.20.0 to 3.20.1
```

## 0.7.3 (2020-10-08)

**Changes:**

* Minor hug fixes and clean ups, see all changes

**All changes:**

```
d2e5a33 mdns: Supress decoding errors
fb8c621 mrp: Don't use deprecated home_hold internally
dc52b5a mrp: Ack client updates messages
925f2b4 mdns: Bind to port 5353 instead of random port
8e54c64 build(deps): bump flake8 from 3.8.3 to 3.8.4
f97ad68 build(deps): bump pytest from 6.1.0 to 6.1.1
08b7229 build(deps): bump pytest from 6.0.2 to 6.1.0
e4172fa build(deps): bump pytest from 6.0.1 to 6.0.2
de13ca1 build(deps-dev): bump tox from 3.19.0 to 3.20.0
319cd5c build(deps): bump pydocstyle from 5.1.0 to 5.1.1
0108425 build(deps): bump black from 19.10b0 to 20.8b1
1be9aaa gha: Bump codecov to 1.0.13
7af56cb build(deps): bump pdoc3 from 0.8.5 to 0.9.1
3654385 deps: Lower zeroconf requirement to 0.28.0
954171c net: Change accidental info to debug log
97e2579 build(deps): bump pdoc3 from 0.8.4 to 0.8.5
ba7c581 build(deps): bump zeroconf from 0.28.1 to 0.28.2
8400103 build(deps): bump pytest-xdist from 2.0.0 to 2.1.0
```

## 0.7.2 (2020-08-24)

**Changes:**

* Handle authority records in MDNS which fixes:
  `NotImplementedError: nscount > 0`
* Do not require ACK for some remote control commands
  to be compatible with tvOS 14 (beta)
* Abort scanning early when expected device (by identifier)
  is found

**All changes:**

```
6a692e0 build(deps): bump pydocstyle from 5.0.2 to 5.1.0
5627304 build(deps): bump codecov from 2.1.8 to 2.1.9
7c40bce scan: Abort when device with identifier found
92ccf6c mrp: Require no ACK for HID messages
fe4ea4d build(deps): bump zeroconf from 0.28.0 to 0.28.1
b020b67 mdns: Add support for authority records
```

## 0.7.1 (2020-08-16)

**Changes:**

* Fixed lots of issues with scanning
* Improved performance for MRP playing information
* Fixed wrong identifier for DMAP when MDNS name collision exists
* Support for python 3.9 (beta)

**All changes:**

```
8cec795 gha: Retry tox if first run fails
d77c56f build(deps): bump pytest-xdist from 1.34.0 to 2.0.0
a424f08 build(deps): bump pytest-cov from 2.10.0 to 2.10.1
bb703ca scan: Fix DMAP identifier when name collides
2bcafb4 conf: Convert tests to pytest
91de62f build(deps): bump pytest from 5.4.3 to 6.0.1
68992d4 mdns: Fixes to make tests more stable
f64b357 mdns: Extract functional tests
8d4edf3 mdns: Fix multicast issues
d30350e support: Add level to log_binary
3ffa1ff build(deps-dev): bump tox from 3.18.0 to 3.19.0
ff0ba00 build(deps): bump pytest-xdist from 1.33.0 to 1.34.0
dfbd428 build(deps): bump deepdiff from 5.0.1 to 5.0.2
d2d17b3 build(deps-dev): bump tox from 3.17.1 to 3.18.0
a82d7e1 scan: Remove check if host is on any local subnet
23accc6 gha: Run tests with python 3.9
45d08c8 api: Convert Union[x, NoneType] to Optional[x]
104620c api: Print diff when API docs mismatch
c173afb Resolve performance slowdown with copying playing data
14192d9 build(deps): bump codecov from 2.1.7 to 2.1.8
c05c351 build(deps-dev): bump tox from 3.17.0 to 3.17.1
63ce14f build(deps): bump pytest-timeout from 1.4.1 to 1.4.2
71d1f80 build(deps-dev): bump tox from 3.16.1 to 3.17.0
61289c6 build(deps): bump pdoc3 from 0.8.3 to 0.8.4
```

## 0.7.0 (2020-07-14)

**Changes:**

* Input actions (single/double tap and hold) are now supported
* Support for aiohttp 4 (only tested with pre-release)
* Possibility to wait for power state change in turn_on and turn_off
* TCP keep-alive configured to detect stale connections
* Implement custom scanning (not using 3rd party zeroconf library)
* Switch back to zeroconf from aiozeroconf for service publishing
* Deep sleep detection when scanning
* Tunnel mode has been added to atvproxy
* A delay command has been added to atvremote
* Fix (potentially) for hanging connection after receiving artwork (MRP)
* Fix bug in device state when app reports invalid playback rate (MRP)
* Fix broken repeat handling (MRP)
* Fix broken pairing (DMAP)
* Fix missing application name (MRP)

**Notes:**

* This release contains re-written scanning logic which hopefully
  makes scanning more reliable (not 100% foolproof though). This
  re-write gives support for deep-sleep detection and better device
  model detection. It is however less tested, so bugs probably still
  exist. Please write bug reports.
* TCP keep-alive and timeout timers are now configured. Keep alive
  messages are sent regularly and the connection will time out (and
  disconnect) after 20 seconds of no replies.


**All changes:**

```
c7f8166 cq: Minor clean ups
9758d3d mrp: Potential fix for protocol hangs
2f2393e dmap: Fix pairing endpoint bug
8419376 scan: Migrate back to zeroconf from aiozeroconf
558213a build(deps): bump pytest-xdist from 1.32.0 to 1.33.0
d1bb536 scan: Get device model from mdns
cb010bf devinfo: Add lookup for internal names
e2b95fe gha: Enable codecov again
11b297b atvremote: Add delay command
087fc50 device_info: Add some tvOS build numbers
ef2849b scan: Extract scanners to a support module
9bcfafd mdns: Rename udns module to mdns
405ce01 scan: Add support for deep sleep detection
c1ac7ce udns: Add Response type to unicast and multicast
100aeee mrp: Update protobuf for language options.
25d1f4b if: Add support for input actions in protocols
da4c769 if: Add InputAction for relevant buttons
16f8e92 build(deps): bump deepdiff from 5.0.0 to 5.0.1
c81d180 build(deps-dev): bump tox from 3.16.0 to 3.16.1
ac842cd scan: Handle sleep proxy responses
8dea1f6 udns: Return service objects
0128a7e udns: Fix some unicode issues
c48e979 scan: Add and use parser for MDNS services
73d3a1b udns: Add support for A records
83f0a42 udns: Extract test helpers to module
0f362a0 build(deps): bump pdoc3 from 0.8.1 to 0.8.3
eb4bcf6 build(deps-dev): bump tox from 3.15.2 to 3.16.0
575dab6 build(deps): bump pytest-asyncio from 0.12.0 to 0.14.0
2c6f526 build(deps): bump deepdiff from 4.3.2 to 5.0.0
0154375 build(deps): bump mypy from 0.781 to 0.782
0ca534c build(deps): bump mypy from 0.780 to 0.781
d5b24f2 udns: Cancel re-send loops properly
1104e7a cq: Fix broken sleep stub
51bd450 scan: Add more typing
7c3e1a0 scan: Add explicit bind to multicast scan
93f1281 scan: Custom scanning implementation
1ccbc57 net: Add method to get all private addresses
06c54a1 build(deps): bump mypy-protobuf from 1.22 to 1.23
7e33682 build(deps): bump pytest-timeout from 1.4.0 to 1.4.1
127ed5a mrp: Fix repeat state bug
9e10b1f build(deps): bump pytest-timeout from 1.3.4 to 1.4.0
885ebfb build(deps): bump codecov from 2.1.5 to 2.1.7
55efb9f build(deps): bump mypy-protobuf from 1.21 to 1.22
85d81a5 mrp: Use stringify for TLV8 errors
4a30354 hap_tlv8: Add stringify method
72ed37a hap_tlv8: Use enums instead of constants
8c145bf hap_tlv8: Use integer as key instead of string
7ddf8c4 hap_tlv8: Convert to pytest
a26e12c mrp: Move tlv8 to support and rename
52d6237 build(deps): bump codecov from 2.1.4 to 2.1.5
5cf2d4f build(deps): bump pytest-cov from 2.9.0 to 2.10.0
c726511 mrp: Configure TCP keep-alive
7d848eb mrp: Fix state when playback rate is wrong
6f0cb81 build(deps): bump flake8 from 3.8.2 to 3.8.3
cae478a atvproxy: Simplify MRP usage
64c80b2 docs: Various updates to documentation
af1322d build(deps-dev): bump tox from 3.15.1 to 3.15.2
3490e2b build(deps): bump mypy from 0.770 to 0.780
850e8d0 mrp: Clean up player path handling
557f418 cq: Exclude __pycache__ from black
41542a0 gha: Disable codecov as it's broken
688ec71 docs: Add a logo image and favicon
2619360 gha: Remove invalid codecov option
0cb12bd build(deps): bump codecov from 2.1.3 to 2.1.4
e8da6fc power: Add await_new_state argument
2134f88 build(deps): bump pytest from 5.4.2 to 5.4.3
a5cddd1 cq: Support for aiohttp 4
5458a30 mrp: Maintain last known app name
eefbe29 Added information regarding playbackRate issue
f2b5df8 atvproxy: Add tunnel support
be6270d build(deps): bump mypy-protobuf from 1.20 to 1.21
a5e01c6 doc: Add black badge to README
1b86065 build(deps): bump flake8 from 3.8.1 to 3.8.2
cb6166c cq: Add dependabot config
7f443bf build(deps): bump pytest-cov from 2.8.1 to 2.9.0
8316679 build(deps): bump codespell from 1.16.0 to 1.17.1
ef18612 build(deps): bump codecov from 2.1.1 to 2.1.3
d9f9767 build(deps): bump flake8 from 3.7.9 to 3.8.1
3b6e5da build(deps-dev): bump tox from 3.15.0 to 3.15.1
153e798 build(deps): bump codecov from 2.0.22 to 2.1.1
fa32dab build(deps): bump pytest from 5.4.1 to 5.4.2
be953a6 build(deps): bump pytest-asyncio from 0.10.0 to 0.12.0
6883973 tests: Fix minor pytest incompatibilities
194e439 build(deps): bump pytest-xdist from 1.31.0 to 1.32.0
257d152 build(deps-dev): bump tox from 3.14.6 to 3.15.0
96adea5 cq: Run tests with base versions
```

## 0.6.1 (2020-04-28)

**Changes:**

* Fixes compatibility issues with older protobuf versions

**All changes:**

```
230cf9c mrp: Fixes to support older protobuf versions
```

## 0.6.0 (2020-04-28)

**Changes:**

* Stream local files via AirPlay
* Unicast scanning will now wake up sleeping devices automatically
* Support for skip_forward and skip_backward
* Support volume_up and volume_down (DMAP)
* Artwork can be retrieved with custom width and height
* top_menu now goes to main menu on tvOS
* play_pause will be emulated by play/pause on tvOS if not natively supported
* Fix retrieval of artwork with missing identifier
* Many improvements to atvscript (timestamp, exception handling, etc.)

**Notes:**

* Default timeout for HTTP requests (DMAP and AirPlay) has been increased to
  25 seconds to deal with waking up devices
* Weak references are now used for all listeners, see
  https://pyatv.dev/support/troubleshooting if you have any problems
* Unicast scanning for hosts outside of any local subnet will
  result in exceptions.NonLocalSubnetError
* Resources are now properly cleaned up when closing a device, e.g.
  anything playing with AirPlay will be disconnected
* Additional log points have been added and existing log points have been
  changed to be more consistent within pyatv

**All changes:**

```
e81e031 docs: Rename variable in credentials example
206b5de atvremote: Support width/height in artwork_save
f023d88 mrp: Add support for artwork width/height
4f4b85a dmap: Add limited support for artwork width/height
42b38e3 if: Add width and height to artwork method
d9986bc cq: Fix a bunch of TODOs in the code
a4bd413 airplay: Use default timeout for HTTP requests
bd580be docs: Inherit from listener interfaces
c122c00 mrp: Add fallback for play_pause
3ec1fb6 cq: Clean up resources when closing a device
e22b2a8 dmap: Minor log improvements to DAAP
6c41457 mrp: Fix TransationMessage definition
ff7dbad mrp: Add more missing protobuf definitions
2cd723a cq: Fix warnings from tests
15aed64 atvscript: Add start log entry
d0ca073 docs: Add apps section to FAQ
5f7d141 knock: Support for continuously knocking ports
95884fb udns: Send UDNS request every second
751e691 udns: Port knock to wake sleeping devices
b533935 net: Change timeout to 25 seconds
32ce9ea mrp: Make connection listener into weakref
5544cd8 cq: Various debug log improvements
d451bfd scan: Fix type bug in scan_hosts
8f56efb dmap: Add support for volume_up and volume_down
4c7140b docs: Clarify when no PIN is displayed
261b0b2 gha: Test on windows-latest
991ea6f udns: Verify address in any local subnet
2887a05 build(deps): bump pdoc3 from 0.8.0 to 0.8.1
d79ba1a docs: Add stacktrace key to atvscript
7fb6ed0 mrp: Change topmenu to go to main menu
62b3e4e if: Use weak references for listeners
8fc8d90 docs: Add type annotations for properties
cb3b08c build(deps): bump pdoc3 from 0.7.5 to 0.8.0
2be2a24 atvscript: Add debug flag
91c1b98 atvscript: Make more robust to errors
1b2262d mrp: Fix broken protobuf messages
9faed04 if: Change close to not be a coroutine
a821a2c airplay: Add support for streaming local file
13cc9d3 mrp: Make Playing objects immutable
e874ad2 docs: Minor updates for skip_forward/backward
d16076a dmap: Implement skip_forward and skip_backward
6786d89 mrp: Implement skip_forward and skip_backward
9fe9f83 if: Add skip_forward and skip_backward
b9fb540 cq: Add codespell for code and docs
40d54ec cq: Improvements to tox
89892bd atvscript: Add timestamp to output
755c507 atvscript: Add device listener
30c4f1f mrp: Add error codes
32b6c55 mrp: Fix naming bug I introduced
64f98fd mrp: Add error code to SendCommandResultMessage
b82379c release: Adapt script to recent changes
ca29655 release: Use current commit instead of master
5ca58a7 atvscript: Flush output of each line
feca6ea mrp: Handle artwork without identifier
1486f62 atvscript: Treat empty strings as None
b7f5d01 scan: Clean up pending service browsers
ee5b828 Update issue templates
37c26ee build(deps): bump mypy-protobuf from 1.19 to 1.20
a32aaa4 docs: Exclude internal function
768a449 bug: Make pairing interface consistent
33775cd mrp: Add tvOS 13.4 build number
44297ac docs: Update FAQ regarding AirPlay
861fc9b fake_device: Add initial support for AirPlay
5aeeed6 fake_device: Initial support for DMAP
3953301 fake_device: Add protocol flag for MRP
3ad6450 fake_device: Add demo mode in fake_device
4212173 tests: Multi-client support for fake MRP service
fe24dc4 tests: Use one fake device with multiple services
72a79ba tests: Refactor fake devices
8a0f057 tests: Move all fake devices to common directory
e6b80dd tests: Begin extraction of fake AirPlay state
67963d1 tests: Begin extraction of fake DMAP state
33e4c2c tests: Begin extraction of fake MRP state
84dec4a scripts: Add features to atvscript
20a2027 scan: Remove non-breaking space
af2c4a2 docs: Fix typo in link
24087d8 gha: Remove push from trigger
0dcc36f docs: Add edit link at bottom
7abc2e3 docs: Various minor updates
04c86fe tests: Break out state in MRP fake device
f088bcd scripts: Add start of fake device script
1f8480d tests: Clean up asserts in fake devices
```

## 0.5.0 (2020-03-19)

**Changes:**

* Add power interface
* Add device information interface
* Add playing app interface
* New scripts: atvscript and atvproxy
* External interface now has type hints
* Pure AirPlay devices are no longer returned by scan
* Files have been moved around and the public interface
  is now well-defined
* Documentation has moved to pyatv.dev

*Breaking Changes:*

* suspend and wakeup in the remote control interface are now
  deprecated. They did not work very well. Use the power interface
  instead.
* Black is now used for linting and black does not support
  python 3.5, so support for python 3.5 has been dropped.
* helpers.auto_connect is now a coroutine

**Notes:**

* Lots of updates to documentation and tests have been made
* An API reference is now available at pyatv.dev

**All changes:**

```
0cf6689 mrp: Support volume control features
11b59f1 protobuf: Workaround for older versions
9398768 docs: Minor fixes
947bb04 tests: Make push updates test more robust
40a45ea tests: Add initial tests for atvscript
e3af8fc tests: Break out script test environment
fae8525 tests: Fix broken sleep stub
865483a scan: Wait for pending tasks
365ae6d scripts: Add atvscript
10af6e9 scripts: Add atvproxy
b96098e scripts: Move atvremote
0f8e5cd build(deps): bump codecov from 2.0.16 to 2.0.21
a2143d5 build(deps): bump pytest from 5.3.5 to 5.4.1
f45f879 test: Migrate from asynctest to pytest-asyncio
b3fa547 docs: Add links to API reference
f41cc11 docs: Add documentation for app support
b91f5d5 mrp: Add app support
0dbe373 if: Add interface for app
bdc01f3 docs: Fix relative links
5661c36 docs: Fix baseurl
e3bcb7a docs: Change domain to pyatv.dev
e8e364c Create CNAME
3917092 build(deps): bump mypy from 0.761 to 0.770
766b438 docs: Clean up and improve documentation
3c99ae6 features: Add tests for features
364ac39 atvremote: Add support for features
6a97526 docs: Add documentation for features
a63ed69 mrp: Add basic support for features
1cee19c dmap: Add basic support for features
a025cdd if: Add interface for supported features
dbc75fa protobuf: Update messages
86cecad docs: Add API documentation
1912891 mrp: Subscribe to volume updates
778257f cq: Add typing hints to public interface
6bf74e7 cq: Handle invalid credentials
5a6c8de cq: Remove need for ed25519
b2b8e58 cq: Remove need for curve25519-donna
18d3894 cq: Remove need for tlslite-ng
cf3048d if: Add support for play_pause
181adc9 cq: Move internal modules to support directory
eaf5176 cq: Move from pylint to black for linting
5e056f1 if: Deprecate suspend and wakeup
08b0b37 scan: Do not include pure AirPlay devices
```

## 0.4.1a1 (2020-03-02)

**Changes:**

* Add power interface
* Add device information interface
* Convert module (convert.py) is now public API

**Notes:**

* General improvements to protobuf handling (for developers)

**All changes:**

```
e4f6590 devinfo: Minor clean ups
d645d5a devinfo: Add device_info to atvremote
33622b8 devinfo: Get version from osvers
e3ad40b devinfo: Add documentation
df8f6a1 devinfo: Clean up zeroconf properties
908d2ea devinfo: Add support for device info
8da7fd2 devinfo: Add helpers for extracting device info
cb8d73a if: Add interface for device information
d8624fd MRP Power State support (#458)
1f97630 if: Tidy up convert module and make it public
ce926b0 protobuf: Move pyatv imports in protobuf.py
554d965 gha: Trigger on both push and pull_request
a8ab245 gh: Run actions on pull requests
024284b mrp: Add some protobuf definitions for voice
ac3ae13 mrp: Wait for command responses
c765dbe mrp: Download protoc and verify generated code
070946f Bump codecov from 2.0.15 to 2.0.16
```

## 0.4.0 (2020-02-20)

**Changes:**

The 0.4.0 release is here! It contains too many changes to list.
Have a glance a pre-releases to get an idea of what it contains.

**All changes:**

```
46a5399 docs: Add basic migration instructions
f0789c1 Bump mypy-protobuf from 1.18 to 1.19
```

## 0.4.0a16 (2020-02-18)

**Changes:**

* Fixes position in MRP

**All changes:**

```
511e83e mrp: Fix calcuation of position
1ba1030 scan: Remove non-breaking space in names
```

## 0.4.0a15 (2020-02-15)

**Changes:**

* Fix minor state bug and implement seeking in MRP

**All changes:**

```
9ab37c6 Change zeroconf warning to debug
3155e84 mrp: Fix device state handling
7b6aacb Bump mypy-protobuf from 1.17 to 1.18
```

## 0.4.0a14 (2020-02-11)

**Changes:**

* Added some missing DMAP tags
* Limit log print outs to not flood logs
* Minor updates to protobuf definitions

**All changes:**

```
5f46dac Consolidate protobuf scripts into one script
0cfb9fc Ignore some unknown DMAP tags
ad95943 Supress unknown DMAP media kind
413eb32 Add some missing DMAP tags
bfa5a45 New protobuf message and minor updates
8ee3183 Limit log printouts for binary data att protobuf
```

## 0.4.0a13 (2020-01-31)

**Changes:**

* Fixed bug where device state would be reported as "paused"
  when playing (yielding incorrect position as side-effect). This
  also fixes delta updates, where metadata would sometimes be
  lost.
* Fixed bug where a crash would occur if a device had a = (0x3D)
  in its MAC-address
* Added artwork_id to metadata that gives a unique id for artwork
* Use cache for artwork that saves the latest four artworks
* Identifiers in config is now prioritized in order
  MRP, DMAP and AirPlay
* AirPlay is not handled specially in config now. If no AirPlay
  service is added, no service will be implicitly created.
* Error handling (raised exceptions) are now more consistent
  when pairing

*Breaking changes*

* AirPlay interface has been renamed to "stream", e.g. use
  atv.stream.play_url instead of atv.airplay.play_url.

**Notes:**

* Running tests on Windows works again
* This release contains a lot new test coverage and all "common"
  functional tests have been ported to MRP
* Last documentation have been migrated to markdown
* Moved from travis to GitHub actions

**All changes:**

```
635ec68 Change last files from rst to markdown
cff609d Remove AirPlay as special case
63f230a Change AirPlay interface to Stream interface
d11fba1 Add priority to identifiers in config
17c685d Improve device state and delta updates in MRP
bcb69de Use content id as hash in MRP
7443118 Bump mypy-protobuf from 1.16 to 1.17
c1c9dac Bump pytest from 5.3.4 to 5.3.5
9aff539 Fixes to push updates, error handling and more
dec3cb3 Minor clean ups and additional coverage
a383b66 Add timestamp to debug log in atvremote
be01d8a Add codecov upload to test workflow
713694a Remove travis configuration
0d06c5a Fix tests on Windows
a95a3dc Run tests with GitHub actions
11b8155 Add simple LRU cache for artwork
bdf76e0 Fix bug i TXT handling in UDNS
61cd843 Add tests for MRP authentication
830448f Extract SRP server code in proxy
cb0018a Unicast scanning does not work between networks
bdfcac0 Use pytest-xdist in tox
6b50f2a Migrate last common functional tests
1e67b95 Move more functional tests to common
b3b9225 Bump pytest from 5.3.3 to 5.3.4
d49837d Re-raise OSError during AirPlay pairing on errors
6ed3dee Bump pytest from 5.3.2 to 5.3.3
```

## 0.4.0a12 (2020-01-19)

**Changes:**

* Minor bug fixes and improvements, see log below

**All changes:**

```
0c68936 Some updates to the MRP proxy
c25fe5d Add temporary test for credentials in atvremote
1b9f395 Initial clean-up of pairing and auth exceptions
72fc6f0 Release resources when closing in DMAP pairing
f2d91b0 Avoid closing external aiohttp session in MRP
05abc25 Bump typed-ast from 1.4.0 to 1.4.1
e00c6a4 Set unicast bit in qtype field
6a55c73 Bump pydocstyle from 5.0.1 to 5.0.2
34cb7ff Handle NaN durations in MRP
```

## 0.4.0a11 (2020-01-09)

**Changes:**

* Support for unicast scanning
* Added wakeup command in remote control interface
* Mostly quality release with minor bug fixes and more tests

**Notes:**

* Breaking changes in this release due to change to enums (6018ba2)

**All changes:**

```
998e77c Minor bug fixes
d0eacb0 Bump flake8 from 3.7.8 to 3.7.9
a5c8d68 Bump mypy from 0.730 to 0.761
a9aa1c4 Bump pydocstyle from 4.0.1 to 5.0.1
98a72bb Support for scanning specific hosts
a3560e5 Bump pytest-timeout from 1.3.3 to 1.3.4
64fcd2e Bump mypy-protobuf from 1.15 to 1.16
87f07ee Clean up tox and move from coveralls to codecov
6496548 Refactor scanning code
6018ba2 Change from constants to enums in const.py
ca8ae64 Fix position in MRP when elapsed time is missing
deb7374 Additional atvremote tests
4a2b27e Add first "playing" functional test to MRP
5001d18 Rename play_state to device_state
1c5f3b3 Fix flaky home button test in MRP
918e2be Add some additional tests for MRP
2f1b32a Add wakeup command to RemoteControl
72e31a9 Update artwork documentation
8d0b4a6 Update feature table in documentation
```

## 0.4.0a10 (2019-12-11)

**Changes:**

* Support for artwork in MRP
* Retry attempts in AirPlay
* Better test coverage

**All changes:**

```
f5f775b Add retry attempts when AirPlay streaming fails
680bdcf Initial support for artwork in MRP
a9f0ca9 Add documentation for manual mode in atvremote
5d89ec9 Add Investigation to issue templates
107c691 Add initial smoke tests for atvremote
e45deba Prepare for adding MRP tests
4644158 Add AirPlay test for new credentials
```

## 0.4.0a9 (2019-12-07)

**All changes:**

```
c25da51 Fix MRP idle state
```

## 0.4.0a8 (2019-12-06)

**Changes:**

* Leading zeros when pairing AirPlay works now

**All changes:**

```
bf71b8f Include all changes from git in CHANGES.rst
3086be5 Create release branch automatically
4e8854a Support leading zeros for PINs in AirPlay
```

## 0.4.0a7 (2019-12-05)

*Noteworthy:*

* Better handling of PINs with leading zeros in MRP
* No re-use of ClientSession in AirPlay hopefully fixes dangling
  connections (i.e. spinng wheel after playback)
* Documentation finalized

**All changes:**

```
ed026dc Add initial script to make releases
514272f Add interface to report device disconnects
6607187 [fix] typo in getting_started.md
703ccc7 Support PINs with leading zeros in MRP
98a4d53 General clean-up of various parts
69a22e0 [fix] Other typo in getting_started.md
b538644 Do not re-use ClientSession for AirPlay
aa8f629 Throw exception if MRP pairing fails
652b039 Finalize documentation for 0.4.0
1cd5508 Add initial text about concepts to documentation
5b51db5 Add badge to LGTM
```

## 0.4.0a6 (2019-11-26)

**All changes:**

```
ffc4b40 Fix connection handling in MRP pairing
```

## 0.4.0a5 (2019-11-26)

**All changes:**

```
96f3b81 Update dmap implementation
f81aeab Update __init__.py
f133fb8 Implement asyncio.sleep
9e9dfdc Add MRP functionality
4765565 Make corrections to MRP flow
2906e34 Return MRP credentials as string after pairing
88bf241 Specify device with -n in atvremote
```

## 0.4.0a4 (2019-11-20)

**Changes:**

```
cfa0514 Fix push updater in MRP
945a2d6 Add set_credentials to conf.AppleTV
0373c5d Add "back off" exception to MRP
32d4e58 Add service property to PairingHandler
81d74cd fixed credentials reference to .service.credentials
1c2029c Use pyatv as title on main page in documentation
```

## 0.4.0a3 (2019-11-15)

Same as a2 (I never learn...).

## 0.4.0a2 (2019-11-15)

Third pre-release. Most stuff is in place now except for tests and documentation.

## 0.4.0a1 (2019-10-08)

Second pre-release which is basically the same as first, but I messed up and missed
a few commits...

## 0.4.0a0 (2019-10-08)

First pre-release of 0.4, too many changes to list. But initial MRP support
is the biggest addition.

## 0.3.9 (2017-12-12)

*Changes*

* Handle re-login properly in case of connection problems or if a device is
  restarted

## 0.3.8 (2017-11-17)

**Changes:**

* Revert some of the earlier AirPlay clean ups from 0.3.5 as that made playback
  less reliable
* Use binary plist instead of text format in play_url to make AirPlay work with
  later versions of tvOS

## 0.3.6 (2017-10-01)

**Changes:**

* Fix string conversion for idle state (#120)

## 0.3.5 (2017-09-26)

**Changes:**

* Fix support for genre (#106)
* Handle playstate idle/0 (#115)
* Improve session handling in AirPlay (#118)

## 0.3.4 (2017-07-18)

**Changes:**

* Add long_description to get description on pypi

## 0.3.3 (2017-07-18)

**Changes:**

* Fixed broken device_id function (always generated same id)

*atvremote:*

* Fixed argument handling, e.g. when using play_url

## 0.3.2 (2017-06-20)

**Notes:**

* Same as 0.3.1 but fixed with pypi

## 0.3.1 (2017-06-20)

**Changes:**

* Add device_id
* Remove developer commands

## 0.3.0 (2017-06-19)

**Changes:**

* Support AirPlay device authentication
* Support arrow keys (left, right, up, down)
* Support scanning for Apple TVs with home sharing disabled
* Support for shuffle and repeat modes
* Support for "stop" button
* Handle additional media kinds
* New "hash" function in Playing API
* Support python 3.6
* Bump aiohttp to 1.3.5 and support 2.0.0+

*atvremote:*

* Multiple commands can be given to atvremote
* Doing "atvremote commands" requires no device and is a lot faster
* All commands now listed with "atvremote commands"
* New "help" command in atvremote
* Fix atvremote exit codes

**Notes:**

* play_url has moved to the new airplay module and no longer
  accepts start position as required argument. This is a
  breaking change!

*Other:*

* Upgrade test tools (pylint, flake, etc.)
* Added documentation to readthedocs

## 0.2.2 (2017-03-04)

**Changes:**

* Allow custom pairing guid when pairing

**Notes:**

* By default, a random pairing guid is now generated when calling
  pyatv.pair_with_apple_tv.

## 0.2.1 (2017-02-28)

**Changes:**

* Always trigger one push update when starting

## 0.2.0 (2017-02-23)

**Changes:**

* Support for push updates
* Fast auto discovery for single device
* Nicer output in "atvremote playing"
* Pairing improvements
* Unpin external dependencies

*Other:*

* Easier version management (internal)
* Code quality improvements (quantifiedcode)

## 0.1.4 (2017-02-11)

**Changes:**

* Added new function: artwork_url
* aiohttp bumped to 1.3.1

## 0.1.3 (2017-02-09)

**Changes:**

* Made it possible to pass a custom ClientSession

**Notes:**

* Renamed topmenu to top_menu which is a breaking change

## 0.1.2 (2017-02-09)

**Changes:**

* aiohttp bumped to 1.3.0
* Fix a potential request leak on error

## 0.1.1 (2017-02-07)

This is the same as 0.1.0 but actually contains everything stated
in the changes.

## 0.1.0 (2017-02-07)

**Changes:**

* Pairing
* Support both HSGID and pairing-guid
* Play media by specifying a URL (via AirPlay)
* atvremote artwork will now save to file (artwork.png)
* Zeroconf bumped to 0.18.0

**Notes:**

* asyncio loop is now passed to pyatv.scan_for_apple_tvs which breaks
  previous API

*Other:*

* Automatic builds with travis
* Code coverage reports with coveralls

## 0.0.1 (2017-02-01)

* Initial version

