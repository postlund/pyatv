A python client library for the Apple TV
========================================
|Build Status| |Coverage Status| |PyPi Package| |Quantifiedcode|

This is a python library for controlling and querying information from an Apple TV. It is async
(python 3.4 syntax) and supports most of the commands that the regular Apple Remote app does as
well as some additional iTunes commands, like changing the media position.

As this library is still at an early development stage, functionality is still missing, bugs
exist and API may change. Look at this as a "technical preview". API is not considered final
until version 1.0 is released.

The MIT license is used for this library.

Features
--------

- Automatic discovery of devices (zeroconf/Bonjour)
- Pairing with devices
- Most buttons (play, pause, next, previous, select, menu, top_menu)
- Fetch artwork in PNG format
- Currently playing (e.g. title, artist, album, total time, etc.)
- Change media position


Requirements
------------

- python>=3.4.2
- zeroconf==0.18.0
- aiohttp==1.3.0

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

    # Manually specify device
    $ atvremote --address 10.0.10.22 --hsgid 00000000-1234-5678-9012- 345678901234 playing
    album: None
    artist: None
    media_type: 1
    play_state: 1
    position: 0
    title: None
    total_time: 0

    # List all commands supported by a device
    $ atvremote -a commands
    Remote control commands:
     - next - Press key next
     - down - Press key down
     - previous - Press key previous
     - set_position - Seek in the current playing media
     - pause - Press key play
     - menu - Press key menu
     - up - Press key up
     - play_url - Play media from an URL on the device
     - select - Press key select
     - right - Press key right
     - top_menu - Go to main menu (long press menu)
     - play - Press key play
     - left - Press key left

    Metadata commands:
     - playing - Return what is currently playing
     - artwork_url - Return artwork URL for what is currently playing (or None)
     - artwork - Return artwork for what is currently playing (or None)

    Playing commands:
     - media_type - What type of media is currently playing, e.g. video, music
     - artist - Artist of the currently playing song
     - position - Current position in the playing media (seconds)
     - title - Title of the current media, e.g. movie or song name
     - album - Album of the currently playing song
     - play_state - Current play state, e.g. playing or paused
     - total_time - Total play time in seconds

Type `atvremote --help` to list all supported commands.

Missing features and improvements
---------------------------------

There are still a lot to do. Here is a summary of currently known missing
functionality and other improvements. GitHub issues will be created for easier
tracking.

Tasks related to library features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Pairing with a device **DONE** (#9)
- Asynchronous auto discovery **DONE**
- Non-polling based API (callbacks) (#8)
- Send URL to AirPlay media **DONE** (#16)
- Arrow keys (up, down, left and right) (#17)
- Allow auto discovery stop after finding a device (#19)
- Better output for "playing" in atvremote (#20)
- Verify compatibility with python > 3.5 (tox) *Pending* (#18)
- Fix exit code in atvremote
- Fix various TODOs in the code

Other tasks
^^^^^^^^^^^^

- Help command to get full help text for a command
- Verify support with Apple TV 4 **DONE** (#3, #7)
- Automatic builds with travis **DONE**
- Write simple smoke test for atvremote
- Improved documentation

  - More examples
  - Better pydoc documentation for classes and methods
  - Manual in docs/
  - Add to readthedocs.io

- Investigate support for additional operations (shuffle, repeat, etc.)

Development
-----------

Fork this project, clone it and run `setup_dev_env.sh` to setup a virtual
environment and install everything needed for development:

.. code:: bash

    git clone https://github.com/postlund/pyatv.git
    cd pyatv
    ./setup_dev_env.sh
    source bin/activate

You can run the tests with `python setup.py test`. Also, make sure that
pylint, flake8 and pydoc passes before committing. This is done automatically
if you run just run `tox`.

When using `atvremote`, pass --developer to enable some developer friendly
commands. You may also pass --debug to get better logging.

.. |Build Status| image:: https://travis-ci.org/postlund/pyatv.svg?branch=master
   :target: https://travis-ci.org/postlund/pyatv
.. |Coverage Status| image:: https://img.shields.io/coveralls/postlund/pyatv.svg
   :target: https://coveralls.io/r/postlund/pyatv?branch=master
.. |PyPi Package| image:: https://badge.fury.io/py/pyatv.svg
   :target: https://badge.fury.io/py/pyatv
.. |Quantifiedcode| image:: https://www.quantifiedcode.com/api/v1/project/bcacf534875647af8005bb089f329918/badge.svg
   :target: https://www.quantifiedcode.com/app/project/bcacf534875647af8005bb089f329918
