CHANGES
=======

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

