# CHANGES

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

