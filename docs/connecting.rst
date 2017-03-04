.. _aiohttp-connecting:

Connecting
==========
When connecting to a device, the IP-address (or hostname) and its login id,
e.g. HSGID, is required. These details can be specified manually or be
automatically discovered if home sharing is enabled.

Custom aiohttp session
----------------------
If you are integrating pyatv in an application that already has a
``ClientSession``, then you might want to re-use that session. You can just
pass it as an optional parameter when connecting:

.. code:: python

    other_session = ... # Some session
    atv = pyatv.connect_to_apple_tv(atv, loop, session=other_session)

If no session is given, a default ``ClientSession`` will be created for you.

.. note::

    When you logout from a device by calling (yield from) ``atv.logout()``,
    the session will be closed. So, if you share the session with other
    instances, you might not want to do that.

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
        atvs = yield from pyatv.scan_for_apple_tvs(loop)
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
Manually specifying the required details is not that hard either (also here
you need to logout):

.. code:: python

    import pyatv
    import asyncio

    NAME = 'My Apple TV'
    ADDRESS = '10.0.10.22'
    LOGIN_ID = '00000000-1111-2222-3333-444444444444' # HSGID
    # LOGIN_ID = '0000000000000001'                   # Pairing guid
    DETAILS = pyatv.AppleTVDevice(NAME, ADDRESS, LOGIN_ID)

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

Specify ``LOGIN_ID`` to be either HSGID or the pairing guid used when pairing
with your device.

API Reference: :py:meth:`pyatv.connect_to_apple_tv`, :py:class:`pyatv.AppleTVDevice`
