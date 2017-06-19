A python client library for the Apple TV
========================================
|Build Status| |Coverage Status| |PyPi Package| |Quantifiedcode| |docs|

This is a python library for controlling and querying information from an Apple TV. It is async
(python 3.4 syntax) and supports most of the commands that the regular Apple Remote app does as
well as some additional iTunes commands, like changing the media position. It implements the
legacy DAAP-protocol and does not support features from the new MediaRemote.framework. Support
for this might be added in the future if that protocol is ever fully reverse engineered.

The MIT license is used for this library.

Features
--------

- Automatic discovery of devices (zeroconf/Bonjour)
- Push updates
- Remote control pairing
- AirPlay stream URL (including tvOS 10.2+)
- Playback controls (play, pause, next, stop, etc.)
- Navigation controls (select, menu, top_menu, arrow keys)
- Fetch artwork in PNG format
- Currently playing (e.g. title, artist, album, total time, etc.)
- Change media position
- Shuffle and repeat

Requirements
------------

- python>=3.4.2
- See documentation for additional libraries

Getting started
---------------

Installing
^^^^^^^^^^

Use pip::

    $ pip install pyatv

Using the API
^^^^^^^^^^^^^

Here is a simple example using auto discovery and printing what is playing:

.. code:: python

    import asyncio
    from pyatv import helpers

    @asyncio.coroutine
    def print_what_is_playing(atv):
        playing = yield from atv.metadata.playing()
        print('Currently playing:')
        print(playing)

    helpers.auto_connect(print_what_is_playing)


Additional and more advanced examples can be found in `examples`.

Using the CLI application
^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to use the reference CLI application as well:

.. code:: bash

    # Automatically discover device (zeroconf)
    $ atvremote -a play
    $ atvremote -a next

    # Scanning for devices on network
    $ atvremote
    Found Apple TVs:
     - Apple TV at 10.0.10.22 (hsgid: 00000000-1234-5678-9012-345678901234)

    Note: You must use 'pair' with devices that have home sharing disabled

    # Manually specify device
    $ atvremote --address 10.0.10.22 --hsgid 00000000-1234-5678-9012- 345678901234 playing
    Media type: Music
    Play state: Playing
      Position: 0/397s (0.0%)

    # Passing multiple commands
    $ atvremote -a next next play playing stop

    # List all commands supported by a device
    $ atvremote -a commands
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
     - artwork_url - Return artwork URL for what is currently playing
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

Most of the core functionality is now in place and API is starting to mature
enough to soon be called "stable". Things on the roadmap are listed below.

Planned tasks
^^^^^^^^^^^^^

- Implement MediaRemoteTV protocol
- Investigate robustness of device scanning
- Extend AirPlay support

  - Easy streaming of local files

Minor tasks
^^^^^^^^^^^

- Help command to get full help text for a command (atvremote) **DONE**
- Write simple smoke test for atvremote
- Improved documentation

  - More examples **Considered DONE**
  - Better pydoc documentation for classes and methods
  - Manual in docs/ **DONE**
  - Add to readthedocs.io **DONE**

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

When using ``atvremote``, pass ``--developer`` to enable some developer friendly
commands. You may also pass ``--debug`` to get better logging.

.. |Build Status| image:: https://travis-ci.org/postlund/pyatv.svg?branch=master
   :target: https://travis-ci.org/postlund/pyatv
.. |Coverage Status| image:: https://img.shields.io/coveralls/postlund/pyatv.svg
   :target: https://coveralls.io/r/postlund/pyatv?branch=master
.. |PyPi Package| image:: https://badge.fury.io/py/pyatv.svg
   :target: https://badge.fury.io/py/pyatv
.. |Quantifiedcode| image:: https://www.quantifiedcode.com/api/v1/project/bcacf534875647af8005bb089f329918/badge.svg
   :target: https://www.quantifiedcode.com/app/project/bcacf534875647af8005bb089f329918
.. |docs| image:: https://readthedocs.org/projects/pyatv/badge/?version=master
   :alt: Documentation Status
   :scale: 100%
   :target: https://pyatv.readthedocs.io/en/master/?badge=latest
