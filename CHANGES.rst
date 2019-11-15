CHANGES
=======

0.4.0a3 (2019-11-15)
--------------------

Same as a2 (I never learn...).

0.4.0a2 (2019-11-15)
--------------------

Third pre-release. Most stuff is in place now except for tests and documentation.

0.4.0a1 (2019-10-08)
--------------------

Second pre-release which is basically the same as first, but I messed up and missed
a few commits...

0.4.0a0 (2019-10-08)
--------------------

First pre-release of 0.4, too many changes to list. But initial MRP support
is the biggest addition.

0.3.9 (2017-12-12)
------------------

Changes:

- Handle re-login properly in case of connection problems or if a device is
  restarted

0.3.8 (2017-11-17)
------------------

Changes:

- Revert some of the earlier AirPlay clean ups from 0.3.5 as that made playback
  less reliable
- Use binary plist instead of text format in play_url to make AirPlay work with
  later versions of tvOS

0.3.6 (2017-10-01)
------------------

Changes:

- Fix string conversion for idle state (#120)

0.3.5 (2017-09-26)
------------------

Changes:

- Fix support for genre (#106)
- Handle playstate idle/0 (#115)
- Improve session handling in AirPlay (#118)

0.3.4 (2017-07-18)
------------------

Changes:

- Add long_description to get description on pypi

0.3.3 (2017-07-18)
------------------

Changes:

- Fixed broken device_id function (always generated same id)

atvremote:

- Fixed argument handling, e.g. when using play_url

0.3.2 (2017-06-20)
------------------

Notes:

- Same as 0.3.1 but fixed with pypi

0.3.1 (2017-06-20)
------------------

Changes:

- Add device_id
- Remove developer commands

0.3.0 (2017-06-19)
------------------

Changes:

- Support AirPlay device authentication
- Support arrow keys (left, right, up, down)
- Support scanning for Apple TVs with home sharing disabled
- Support for shuffle and repeat modes
- Support for "stop" button
- Handle additional media kinds
- New "hash" function in Playing API
- Support python 3.6
- Bump aiohttp to 1.3.5 and support 2.0.0+

atvremote:

- Multiple commands can be given to atvremote
- Doing "atvremote commands" requires no device and is a lot faster
- All commands now listed with "atvremote commands"
- New "help" command in atvremote
- Fix atvremote exit codes

Notes:

- play_url has moved to the new airplay module and no longer
  accepts start position as required argument. This is a
  breaking change!

Other:

- Upgrade test tools (pylint, flake, etc.)
- Added documentation to readthedocs

0.2.2 (2017-03-04)
------------------

Changes:

- Allow custom pairing guid when pairing

Notes:

- By default, a random pairing guid is now generated when calling
  pyatv.pair_with_apple_tv.

0.2.1 (2017-02-28)
------------------

Changes:

- Always trigger one push update when starting

0.2.0 (2017-02-23)
------------------

Changes:

- Support for push updates
- Fast auto discovery for single device
- Nicer output in "atvremote playing"
- Pairing improvements
- Unpin external dependencies

Other:

- Easier version management (internal)
- Code quality improvements (quantifiedcode)

0.1.4 (2017-02-11)
------------------

Changes:

- Added new function: artwork_url
- aiohttp bumped to 1.3.1

0.1.3 (2017-02-09)
------------------

Changes:

- Made it possible to pass a custom ClientSession

Notes:

- Renamed topmenu to top_menu which is a breaking change

0.1.2 (2017-02-09)
------------------

Changes:

- aiohttp bumped to 1.3.0
- Fix a potential request leak on error

0.1.1 (2017-02-07)
------------------

This is the same as 0.1.0 but actually contains everything stated
in the changes.

0.1.0 (2017-02-07)
------------------

Changes:

- Pairing
- Support both HSGID and pairing-guid
- Play media by specifying a URL (via AirPlay)
- atvremote artwork will now save to file (artwork.png)
- Zeroconf bumped to 0.18.0

Notes:

- asyncio loop is now passed to pyatv.scan_for_apple_tvs which breaks
  previous API

Other:

- Automatic builds with travis
- Code coverage reports with coveralls

0.0.1 (2017-02-01)
------------------

- Initial version

