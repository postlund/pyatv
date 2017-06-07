.. pyatv documentation master file, created by
   sphinx-quickstart on Wed Jan 18 07:55:14 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pyatv: Apple TV Remote Control Library
==========================================

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

Library Installation
--------------------

Use pip::

    $ pip install pyatv


Getting Started
---------------

Connecting to the first automatically discovered device:

.. code:: python

    import asyncio
    from pyatv import helpers

    @asyncio.coroutine
    def print_what_is_playing(atv):
        playing = yield from atv.metadata.playing()
        print('Currently playing:')
        print(playing)

    helpers.auto_connect(print_what_is_playing)

Connecting to a specific device:

.. code:: python

    import pyatv
    import asyncio

    NAME = 'My Apple TV'
    ADDRESS = '10.0.10.22'
    LOGIN_ID = '00000000-1111-2222-3333-444444444444'
    DETAILS = pyatv.AppleTVDevice(NAME, ADDRESS, LOGIN_ID)


    @asyncio.coroutine
    def print_what_is_playing(loop, details):
        print('Connecting to {}'.format(details.address))
        atv = pyatv.connect_to_apple_tv(details, loop)

        try:
            playing = yield from atv.metadata.playing()
            print('Currently playing:')
            print(playing)
        except:
            yield from atv.logout()


    loop = asyncio.get_event_loop()
    loop.run_until_complete(print_what_is_playing(loop, DETAILS))


What is LOGIN_ID and where to find it? See :ref:`this<pyatv-finding-devices>`
page.


Dependencies
------------

- python>=3.4.2
- zeroconf>=0.17.7
- aiohttp>=1.3.5
- cryptography>=1.8.1
- curve25519-donna>=1.3, <2
- ed25519>=1.4, <2
- srptools>=0.1.1

Contributing
------------

If you want to contribute, see :ref:`developing<pyatv-developing>` for
more information.

Authors and License
-------------------

``pyatv`` is mainly written by Pierre Ståhl and is availble under the *MIT*
license. You may freely modify and redistribute this package under that
license.

If you do make changes, feel free to send a pull request on GitHub.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   protocol
   finding_devices
   pairing
   connecting
   controlling
   metadata
   airplay
   api
   atvremote
   developing
   testing
   troubleshooting
   faq


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
