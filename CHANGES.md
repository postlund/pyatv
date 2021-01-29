# CHANGES

## 0.7.6 (2021-01-29)

*Changes:*

* DNS parsing has been re-written which should be more stable
  and handle more use cases
* TCP keep-alive has been added to more platforms, FreeBSD being one of them
* Player management has been totally re-written for MRP, so hopefully
  play state should be more accurate now
* A delay has been added to turn\_off (MRP), so it should work again
* A heartbeat loop has been added that sends a "heartbeat" to the device
  every 30s to detect connection problems
* Protobuf definitions have been further lifted to match later tvOS versions

*Notes:*

* Fixed a bug where Playing instancess were not immutable
* Push updates are only issued when something in the Playing instance changed.
  Previously, unrelated changes to the device could trigger push updates with
  the same content in Playing.

*All changes:*

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

*Changes:*

* Revert to use random source port for MDNS
* Fix "Received UpdateClientMessage for unknown player xxx""

*All changes:*

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

*Changes:*

* PIN code screen for MRP will now disappear after pairing
* Less and more compact debug logs in mdns and knock

*All changes:*

```
9f1d1d0 mrp: Verify credentials after pairing
1d799f2 cq: Minor clean ups and fixes
061add1 build(deps): bump codecov from 2.1.9 to 2.1.10
dc31ac9 build(deps-dev): bump tox from 3.20.0 to 3.20.1
```

## 0.7.3 (2020-10-08)

*Changes:*

* Minor hug fixes and clean ups, see all changes

*All changes:*

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

*Changes:*

* Handle authority records in MDNS which fixes:
  `NotImplementedError: nscount > 0`
* Do not require ACK for some remote control commands
  to be compatible with tvOS 14 (beta)
* Abort scanning early when expected device (by identifier)
  is found

*All changes:*

```
6a692e0 build(deps): bump pydocstyle from 5.0.2 to 5.1.0
5627304 build(deps): bump codecov from 2.1.8 to 2.1.9
7c40bce scan: Abort when device with identifier found
92ccf6c mrp: Require no ACK for HID messages
fe4ea4d build(deps): bump zeroconf from 0.28.0 to 0.28.1
b020b67 mdns: Add support for authority records
```

## 0.7.1 (2020-08-16)

*Changes:*

* Fixed lots of issues with scanning
* Improved performance for MRP playing information
* Fixed wrong identifier for DMAP when MDNS name collision exists
* Support for python 3.9 (beta)

*All changes:*

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

*Changes:*

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

*Notes:*

* This release contains re-written scanning logic which hopefully
  makes scanning more reliable (not 100% foolproof though). This
  re-write gives support for deep-sleep detection and better device
  model detection. It is however less tested, so bugs probably still
  exist. Please write bug reports.
* TCP keep-alive and timeout timers are now configured. Keep alive
  messages are sent regularly and the connection will time out (and
  disconnect) after 20 seconds of no replies.


*All changes:*

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

*Changes:*

* Fixes compatibility issues with older protobuf versions

*All changes:*

```
230cf9c mrp: Fixes to support older protobuf versions
```

## 0.6.0 (2020-04-28)

*Changes:*

* Stream local files via AirPlay
* Unicast scanning will now wake up sleeping devices automatically
* Support for skip_forward and skip_backward
* Support volume_up and volume_down (DMAP)
* Artwork can be retrieved with custom width and height
* top_menu now goes to main menu on tvOS
* play_pause will be emulated by play/pause on tvOS if not natively supported
* Fix retrieval of artwork with missing identifier
* Many improvements to atvscript (timestamp, exception handling, etc.)

*Notes:*

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

*All changes:*

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

*Changes:*

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

*Notes:*

* Lots of updates to documentation and tests have been made
* An API reference is now available at pyatv.dev

*All changes:*

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

*Changes:*

* Add power interface
* Add device information interface
* Convert module (convert.py) is now public API

*Notes:*

* General improvements to protobuf handling (for developers)

*All changes:*

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

*Changes:*

The 0.4.0 release is here! It contains too many changes to list.
Have a glance a pre-releases to get an idea of what it contains.

*All changes:*

```
46a5399 docs: Add basic migration instructions
f0789c1 Bump mypy-protobuf from 1.18 to 1.19
```

## 0.4.0a16 (2020-02-18)

*Changes:*

* Fixes position in MRP

*All changes:*

```
511e83e mrp: Fix calcuation of position
1ba1030 scan: Remove non-breaking space in names
```

## 0.4.0a15 (2020-02-15)

*Changes:*

* Fix minor state bug and implement seeking in MRP

*All changes:*

```
9ab37c6 Change zeroconf warning to debug
3155e84 mrp: Fix device state handling
7b6aacb Bump mypy-protobuf from 1.17 to 1.18
```

## 0.4.0a14 (2020-02-11)

*Changes:*

* Added some missing DMAP tags
* Limit log print outs to not flood logs
* Minor updates to protobuf definitions

*All changes:*

```
5f46dac Consolidate protobuf scripts into one script
0cfb9fc Ignore some unknown DMAP tags
ad95943 Supress unknown DMAP media kind
413eb32 Add some missing DMAP tags
bfa5a45 New protobuf message and minor updates
8ee3183 Limit log printouts for binary data att protobuf
```

## 0.4.0a13 (2020-01-31)

*Changes:*

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

*Notes:*

* Running tests on Windows works again
* This release contains a lot new test coverage and all "common"
  functional tests have been ported to MRP
* Last documentation have been migrated to markdown
* Moved from travis to GitHub actions

*All changes:*

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

*Changes:*

* Minor bug fixes and improvements, see log below

*All changes:*

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

*Changes:*

* Support for unicast scanning
* Added wakeup command in remote control interface
* Mostly quality release with minor bug fixes and more tests

*Notes:*

* Breaking changes in this release due to change to enums (6018ba2)

*All changes:*

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

*Changes:*

* Support for artwork in MRP
* Retry attempts in AirPlay
* Better test coverage

*All changes:*

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

*All changes:*

```
c25da51 Fix MRP idle state
```

## 0.4.0a8 (2019-12-06)

*Changes:*

* Leading zeros when pairing AirPlay works now

*All changes:*

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

*All changes:*

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

*All changes:*

```
ffc4b40 Fix connection handling in MRP pairing
```

## 0.4.0a5 (2019-11-26)

*All changes:*

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

*Changes:*

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

*Changes:*

* Revert some of the earlier AirPlay clean ups from 0.3.5 as that made playback
  less reliable
* Use binary plist instead of text format in play_url to make AirPlay work with
  later versions of tvOS

## 0.3.6 (2017-10-01)

*Changes:*

* Fix string conversion for idle state (#120)

## 0.3.5 (2017-09-26)

*Changes:*

* Fix support for genre (#106)
* Handle playstate idle/0 (#115)
* Improve session handling in AirPlay (#118)

## 0.3.4 (2017-07-18)

*Changes:*

* Add long_description to get description on pypi

## 0.3.3 (2017-07-18)

*Changes:*

* Fixed broken device_id function (always generated same id)

*atvremote:*

* Fixed argument handling, e.g. when using play_url

## 0.3.2 (2017-06-20)

*Notes:*

* Same as 0.3.1 but fixed with pypi

## 0.3.1 (2017-06-20)

*Changes:*

* Add device_id
* Remove developer commands

## 0.3.0 (2017-06-19)

*Changes:*

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

*Notes:*

* play_url has moved to the new airplay module and no longer
  accepts start position as required argument. This is a
  breaking change!

*Other:*

* Upgrade test tools (pylint, flake, etc.)
* Added documentation to readthedocs

## 0.2.2 (2017-03-04)

*Changes:*

* Allow custom pairing guid when pairing

*Notes:*

* By default, a random pairing guid is now generated when calling
  pyatv.pair_with_apple_tv.

## 0.2.1 (2017-02-28)

*Changes:*

* Always trigger one push update when starting

## 0.2.0 (2017-02-23)

*Changes:*

* Support for push updates
* Fast auto discovery for single device
* Nicer output in "atvremote playing"
* Pairing improvements
* Unpin external dependencies

*Other:*

* Easier version management (internal)
* Code quality improvements (quantifiedcode)

## 0.1.4 (2017-02-11)

*Changes:*

* Added new function: artwork_url
* aiohttp bumped to 1.3.1

## 0.1.3 (2017-02-09)

*Changes:*

* Made it possible to pass a custom ClientSession

*Notes:*

* Renamed topmenu to top_menu which is a breaking change

## 0.1.2 (2017-02-09)

*Changes:*

* aiohttp bumped to 1.3.0
* Fix a potential request leak on error

## 0.1.1 (2017-02-07)

This is the same as 0.1.0 but actually contains everything stated
in the changes.

## 0.1.0 (2017-02-07)

*Changes:*

* Pairing
* Support both HSGID and pairing-guid
* Play media by specifying a URL (via AirPlay)
* atvremote artwork will now save to file (artwork.png)
* Zeroconf bumped to 0.18.0

*Notes:*

* asyncio loop is now passed to pyatv.scan_for_apple_tvs which breaks
  previous API

*Other:*

* Automatic builds with travis
* Code coverage reports with coveralls

## 0.0.1 (2017-02-01)

* Initial version

