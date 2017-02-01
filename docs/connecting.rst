.. _aiohttp-connecting:

Connecting
==========
NOTE: This page currently only covers auto discovery of devices. Pairing will
be added once that is implemented. You must have home sharing enabled for this
to work.

When connecting to a device, the IP-address (or hostname) and its HSGID is
required. These details can be specified manually or be automatically
discovered if home sharing is enabled.

Code Example: Auto discovery
----------------------------
Using auto discovery makes the connection procedure simple. But do not forget
to logout when you are done, otherwise you will get errors about the aiohttp
session not being closed properly.

.. code:: python

    import pyatv
    import asyncio

    @asyncio.coroutine
    def print_what_is_playing(loop):
        atvs = yield from pyatv.scan_for_apple_tvs()
        atv = pyatv.connect_to_apple_tv(atvs[0], loop)

        try:
            # Do something with atv
        finally:
            yield from atv.logout()


    loop = asyncio.get_event_loop()
    loop.run_until_complete(print_what_is_playing(loop))

API Reference: :py:meth:`pyatv.connect_to_apple_tv`

Code Example: Manual details
----------------------------
Manually specifying the required details is not that hard either:

.. code:: python

    import pyatv
    import asyncio

    NAME = 'My Apple TV'
    ADDRESS = '10.0.10.22'
    HSGID = '00000000-1111-2222-3333-444444444444'
    DETAILS = pyatv.AppleTVDevice(NAME, ADDRESS, HSGID)

    @asyncio.coroutine
    def print_what_is_playing(loop, details):
        atv = pyatv.connect_to_apple_tv(details, loop)

        try:
            # Do something with atv
        except:
            # Do not forget to logout
            yield from atv.logout()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(print_what_is_playing(loop, DETAILS))

API Reference: :py:meth:`pyatv.connect_to_apple_tv`, :py:class:`pyatv.AppleTVDevice`
