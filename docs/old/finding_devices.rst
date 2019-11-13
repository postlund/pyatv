.. _pyatv-finding-devices:

Finding Devices
===============
Finding an Apple TV device on the network is as easy as looking for a
particular Zeroconf/Bonjour service on the network. It announces various kinds
if services, but the one pyatv is looking for ``_appletv-v2._tcp.local.``. It
is announced if home sharing is enabled and contains, amongst other things,
the HSGID (corresponding to the "login id") required when connecting to the
device.

A typical entry as found by the python-zeroconf library might look like this
(some of the data replaced):

.. code:: python

    ServiceInfo(type='_appletv-v2._tcp.local.', name='1111111111111111._appletv-v2._tcp.local.', address=b'\n\x00\n\x16', port=3689, weight=0, priority=0, server='AppleTV-2.local.', properties={b'DFID': b'2', b'PrVs': b'65538', b'hG': b'00000000-1125-ff3b-7f12-111111111111', b'Name': b'Apple\xc2\xa0TV', b'txtvers': b'1', b'atSV': b'65541', b'MiTPV': b'196611', b'EiTS': b'1', b'fs': b'2', b'MniT': b'167845888'})

When doing a scan, the information is extracted from these records and that is
basically all you need. Any client that can list Bonjour services can be used, so
``dns-sd`` on macOS is another alternativ:

.. code:: bash

    $ dns-sd -B _appletv-v2._tcp
    Browsing for _appletv-v2._tcp
    DATE: ---Sat 28 Jan 2017---
    12:07:51.222  ...STARTING...
    Timestamp     A/R    Flags  if Domain               Service Type         Instance Name
    12:07:51.223  Add        2   4 local.               _appletv-v2._tcp.    1111111111111111

But you can of course also use ``atvremote``, see
:ref:`this page<pyatv-atvremote>`.

No home sharing
---------------
If you do not want or can't enable home sharing, you can pair with your device
instead and gain a pairing guid that you can use as login id. See
:ref:`pairing<pyatv-pairing>` for more information about that.

Code Example
------------
Discovering devices is as easy as using ``pyatv.scan_for_apple_tvs``, which is
an async call. A simple example might look like this:

.. code:: python

    import pyatv
    import asyncio

    @asyncio.coroutine
    def discover(loop):
        atvs = yield from pyatv.scan_for_apple_tvs(loop, timeout=5)

        # Devices are now in atvs
        print(atvs)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(discover(loop))

API Reference: :py:meth:`pyatv.scan_for_apple_tvs`

Finding a single device
-----------------------
Under some circumstance you might not care about which device you connect to,
usually when you only have one device on the network. To simplify and speed up
the discovery process, you can set the flag ``abort_on_found`` to ``True``.
This will make ``pyatv.scan_for_apple_tvs`` abort when a device has been found,
thus ignore the timeout and return quicker:

.. code:: python

    atvs = yield from pyatv.scan_for_apple_tvs(
        loop, timeout=5, abort_on_found=True)

This is for instance default behavior when using ``-a`` with atvremote. There's
also a helper method that utilizes this by default:

.. code:: python

    import asyncio
    from pyatv import helpers

    @asyncio.coroutine
    def print_what_is_playing(atv):
        playing = yield from atv.metadata.playing()
        print('Currently playing: ')
        print(playing)

    helpers.auto_connect(print_what_is_playing)

When writing simpler application, ``auto_connect`` can be quite convenient as
it can handle loop management for you. It is also possible to pass an error
handler, that is called when a device is not found. See the API referece for
more details.

API Reference: :py:meth:`pyatv.helpers.auto_connect`
