A python client library for the Apple TV
========================================
|Build Status| |Coverage Status| |PyPi Package| |Quantifiedcode|

This is a python library for controlling and querying information from an Apple TV. It is async
(python 3.4 syntax) and supports most of the commands that the regular Apple Remote app does as
well as some additional iTunes commands, like changing the media position. It implements the
legacy DAAP-protocol and does not support features from the new MediaRemote.framework. Support
for this might be added in the future if that protocol is ever fully reverse engineered.

**Note: AirPlay support is currently broken for tvOS 10.2, see issue #79.**

The MIT license is used for this library.

Features
--------

- Automatic discovery of devices (zeroconf/Bonjour)
- Push updates
- Remote control pairing
- Playback controls (play, pause, next, stop, etc.)
- Navigation controls (select, menu, top_menu, arrow keys)
- Fetch artwork in PNG format
- Currently playing (e.g. title, artist, album, total time, etc.)
- Change media position
- Shuffle and repeat

Requirements
------------

- python>=3.4.2
- zeroconf>=0.17.7
- aiohttp>=1.3.5

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
     - Apple TV at 10.0.10.22 (hsgid: 00000000-1234-5678-9012- 345678901234)

    Note: You must use 'pair' with devices that have home sharing disabled

    # Manually specify device
    $ atvremote --address 10.0.10.22 --hsgid 00000000-1234-5678-9012- 345678901234 playing
    Media type: Music
    Play state: Playing
      Position: 0/397s (0.0%)


    # List all commands supported by a device
    $ atvremote -a commands
    Remote control commands:
     - down - Press key down
     - left - Press key left
     - menu - Press key menu
     - next - Press key next
     - pause - Press key play
     - play - Press key play
     - play_url - Play media from an URL on the device
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
     - media_type - What type of media is currently playing, e.g. video, music
     - play_state - Current play state, e.g. playing or paused
     - position - Current position in the playing media (seconds)
     - repeat - Current repeat mode
     - shuffle - If shuffle is enabled or not
     - title - Title of the current media, e.g. movie or song name
     - total_time - Total play time in seconds

    Other commands:
     - push_updates - Listen for push updates

Type ``atvremote --help`` to list all supported commands.

Missing features and improvements
---------------------------------

Most of the core functionality is now in place and API is starting to mature
enough to soon be called "stable". The next major things to support are device
verification (#79) to make AirPlay work with tvOS (10.2+) again. After that,
implementation of the MediaRemoteTV protocol used by newer devices (tvOS) will
be given a shot.

Minor tasks
^^^^^^^^^^^^

- Help command to get full help text for a command (atvremote)
- Write simple smoke test for atvremote
- Improved documentation

  - More examples
  - Better pydoc documentation for classes and methods
  - Manual in docs/
  - Add to readthedocs.io

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
