A python client library for the Apple TV
========================================
|Build Status| |Coverage Status| |PyPi Package| |Downloads| |docs|

This is a python library for controlling and querying information from an Apple TV. It is built
upon asyncio and supports most of the commands that the regular Apple Remote app does as
well as some additional iTunes commands, like changing the media position. It implements the legacy
DAAP/DMAP-protocol used by older Apple TVs (not running tvOS and devices running tvOS < 13).

Support for the Media Remote Protocol (MRP) used by tvOS is under heavy development. Basic support
is available on the GitHub `master` branch and version 0.4.0 of `pyatv` is planned to have
"usable" support (functionality similar to what is supported by DAAP/DMAP). No date is set for when
0.4.0 is to be released yet.

**This is the development branch containing experimental changes. If you want a stable version,
have a look at the v0.3.x tags.**

This library is licensed under the MIT license.

Features
--------

Here is the feature list by protocol (DMAP = devices not running tvOS, MRP = Apple TV 4 and later):

+-----------------------------------------------------------------+----------+-----------+
| **Feature**                                                     | **DMAP** | **MRP**   |
+-----------------------------------------------------------------+----------+-----------+
| Automatic discovery of devices (zeroconf/Bonjour)               | Yes      | Yes       |
+-----------------------------------------------------------------+----------+-----------+
| Push updates                                                    | Yes      | Yes       |
+-----------------------------------------------------------------+----------+-----------+
| Remote control pairing                                          | Yes      | Yes       |
+-----------------------------------------------------------------+----------+-----------+
| AirPlay stream URL (including tvOS 10.2+)                       | Yes      | Yes       |
+-----------------------------------------------------------------+----------+-----------+
| Playback controls (play, pause, next, stop, etc.)               | Yes      | Yes*      |
+-----------------------------------------------------------------+----------+-----------+
| Navigation controls (select, menu, top_menu, arrow keys)        | Yes      | Yes*      |
+-----------------------------------------------------------------+----------+-----------+
| Fetch artwork in PNG format                                     | Yes      | No        |
+-----------------------------------------------------------------+----------+-----------+
| Currently playing (e.g. title, artist, album, total time, etc.) | Yes      | Partial** |
+-----------------------------------------------------------------+----------+-----------+
| Media type and play state                                       | Yes      | Partial** |
+-----------------------------------------------------------------+----------+-----------+
| Change media position                                           | Yes      | Yes*      |
+-----------------------------------------------------------------+----------+-----------+
| Shuffle and repeat                                              | Yes      | Yes*      |
+-----------------------------------------------------------------+----------+-----------+

*\* Some support exists but has not been thoroughly tested to verify that it works satisfactory*

*\*\* Only stub support exists and is mostly not usable*

Requirements
------------

- python >= 3.5.3
- aiohttp >= 3.0.1, <4
- aiozeroconf >= 0.1.8
- cryptography >= 1.8.1
- curve25519-donna >= 1.3
- ed25519 >= 1.4
- netifaces >= 0.10.0
- protobuf >= 3.4.0
- srptools >= 0.2.0
- tlslite-ng >= 0.7.0

Getting started
---------------

Installing
^^^^^^^^^^

Use pip::

    $ pip install pyatv

NOTE: You need some system packages, run this on debian or similar::

    $ sudo apt-get install build-essential libssl-dev libffi-dev python-dev

To install development version from git::

    $ pip install git+https://github.com/postlund/pyatv.git

Using the API
^^^^^^^^^^^^^

Here is a simple example using auto discovery and printing what is playing:

.. code:: python

    import asyncio
    from pyatv import helpers

    async def print_what_is_playing(atv):
        playing = await atv.metadata.playing()
        print('Currently playing:')
        print(playing)

    helpers.auto_connect(print_what_is_playing)


Additional and more advanced examples can be found in `examples`.

Using the CLI application
^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to use the reference CLI application as well:

.. code:: bash

    # Scanning for devices on network
    $ atvremote scan
    Scan Results
    ========================================
           Name: Apple TV
        Address: 10.0.0.10
    Identifiers:
     - 00:11:22:33:44:55
     - AABBCCDDEEFFAABB
    Services:
     - Protocol: AirPlay, Port: 7000
     - Protocol: DMAP, Port: 3689, Credentials: 00000000-1234-5678-9012-345678901234

           Name: Vardagsrum
        Address: 10.0.0.10
    Identifiers:
     - 01234568-9ABC-DEF0-1234-56789ABCDEF0
     - 55:44:33:22:11:00
    Services:
     - Protocol: MRP, Port: 49152, Credentials: None
     - Protocol: AirPlay, Port: 7000

    # Call commands on specific devices
    $ atvremote -i 00:11:22:33:44:55 play
    $ atvremote -i 55:44:33:22:11:00 next

    # Manually specify device
    $ atvremote -m --id ffeeddccbbaa --address 10.0.10.11 --port 3689 --protocol dmap --device_credentials 00000000-1234-5678-9012-345678901234 playing
    Media type: Music
    Play state: Playing
      Position: 0/397s (0.0%)

    # Passing multiple commands
    $ atvremote -i 00:11:22:33:44:55 next next play playing stop

    # List all commands supported by a device
    $ atvremote commands
    Remote control commands:
     - down - Press key down
     - left - Press key left
     - menu - Press key menu
     - next - Press key next
     - pause - Press key play
     - play - Press key play
     - previous - Press key previous
     - right - Press key right
     - select - Press key select
     - set_position - Seek in the current playing media
     - set_repeat - Change repeat mode
     - set_shuffle - Change shuffle mode to on or off
     - stop - Press key stop
     - top_menu - Go to main menu (long press menu)
     - up - Press key up

    Metadata commands:
     - artwork - Return artwork for what is currently playing (or None)
     - device_id - Return a unique identifier for current device
     - playing - Return what is currently playing

    Playing commands:
     - album - Album of the currently playing song
     - artist - Artist of the currently playing song
     - hash - Create a unique hash for what is currently playing
     - media_type - Type of media is currently playing, e.g. video, music
     - play_state - Play state, e.g. playing or paused
     - position - Position in the playing media (seconds)
     - repeat - Repeat mode
     - shuffle - If shuffle is enabled or not
     - title - Title of the current media, e.g. movie or song name
     - total_time - Total play time in seconds

    AirPlay commands:
     - finish_authentication - End authentication process with PIN code
     - generate_credentials - Create new credentials for authentication
     - load_credentials - Load existing credentials
     - play_url - Play media from an URL on the device
     - start_authentication - Begin authentication proces (show PIN on screen)
     - verify_authenticated - Check if loaded credentials are verified

    Device commands:
     - artwork_save - Download artwork and save it to artwork.png
     - auth - Perform AirPlay device authentication
     - push_updates - Listen for push updates

    Global commands:
     - commands - Print a list with available commands
     - help - Print help text for a command
     - pair - Pair pyatv as a remote control with an Apple TV
     - scan - Scan for Apple TVs on the network

Type ``atvremote --help`` to list all supported commands.

Missing features and improvements
---------------------------------

Most features related to DMAP is already in place and focus is currently on
getting MRP in usable shape. This implies certain API breaking changes need
to happen, thus **0.4.0 will not be API compliant with earlier versions**.

Roadmap is below, but be sure to check out open issues as well. New features
and changes are added there.

Near time
^^^^^^^^^

- Implement MediaRemoteTV protocol (#94)
- Investigate robustness of device scanning (#65, #143, #177, #178)

Later
^^^^^

- Stream local files using AirPlay (#95)

Quality and documentation
^^^^^^^^^^^^^^^^^^^^^^^^^

- Write simple smoke test for atvremote
- Write formal test procedure (#203)
- Improved documentation

  - Better pydoc documentation for classes and methods
  - Migrate documentation to GitHub pages (#205)

Development
-----------

Fork this project, clone it and run `setup_dev_env.sh` to setup a virtual
environment and install everything needed for development:

.. code:: bash

    git clone https://github.com/postlund/pyatv.git
    cd pyatv
    ./setup_dev_env.sh
    source bin/activate

You can run the tests with ``python setup.py test``. Also, make sure that
pylint, flake8 and pydoc passes before committing. This is done automatically
if you run just run ``tox``.

When using ``atvremote``, pass ``--debug`` to get better logging.

.. |Build Status| image:: https://travis-ci.org/postlund/pyatv.svg?branch=master
   :target: https://travis-ci.org/postlund/pyatv
.. |Coverage Status| image:: https://img.shields.io/coveralls/postlund/pyatv.svg
   :target: https://coveralls.io/r/postlund/pyatv?branch=master
.. |PyPi Package| image:: https://badge.fury.io/py/pyatv.svg
   :target: https://badge.fury.io/py/pyatv
.. |docs| image:: https://readthedocs.org/projects/pyatv/badge/?version=master
   :alt: Documentation Status
   :scale: 100%
   :target: https://pyatv.readthedocs.io/en/master/?badge=latest
.. |Downloads| image:: https://pepy.tech/badge/pyatv
   :target: https://pepy.tech/project/pyatv
