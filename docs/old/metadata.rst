.. _pyatv-metadata:

Retrieving metadata
===================
It is possible to get metadata, i.e. what is playing, using two different
methods:

- Manually polling
- Push updates

Polling metadata from the device works very similar to the remote control
API, but one asynchronous call will return an object containing all metadata.
This is to lower the amount of device calls needed. Artwork is retrieved
separately.

When using push updates, new updates are *pushed* from the Apple TV when
someting of interest happens. The exact same data that is available when
polling, is passed to a callback provided by the API user. Please see the
example further down for more details.

.. note::

    Only what is currently playing is supported by the push API. Artwork
    must still be polled.

What is currently playing
-------------------------
To retrieve what is currently playing, use the asynchronous playing method:

.. code:: python

    playing = yield from atv.metadata.playing()

You can easily extract fields like title, album or media type. See
:py:class:`pyatv.interface.Playing` and :py:mod:`pyatv.const`.

Artwork
-------
To retrieve the artwork, use the asynchronous artwork method:

.. code:: python

    artwork = yield from atv.metadata.artwork()

Remember that the artwork (which is a PNG file) is relatively large, so you
should try to minimize this call. More information is available at
:py:meth:`pyatv.interface.Metadata.artwork`.

It is also possible to get an artwork URL instead by using ``artwork_url()``.
In this case, the same URL will always be returned as long as current
session is valid and no check is performed if artwork is available (user of
the library must handle this). An example:

.. code:: python

    artwork = yield from atv.metadata.artwork_url()

Device ID
---------
A unique SHA256 identifier can be generated to separate devices from one another:

.. code:: python

    device_id = atv.metadata.device_id

.. note::

    This id is based on the device address solely. No domain name resolution is
    performed, so different identifiers will be returned for the same device
    depending on if an IP-address is specified or a domain name. This might change
    in the future.

Hash
----
To simplify detection if content has changed between retrieval of what is
currently playing, a unique hash can be generated. It is a SHA256 hash based
on the following data:

- Title
- Artist
- Album
- Total time

These properties has been selected as they are in general unique for the same
content. No guarantee is however given that the same hash is not given for
different content nor the same content. It can be used as a fair guess.

.. code:: python

    playing = yield from atv.metadata.playing()
    ...  # Some time later
    playing2 = yield from atv.metadata.playing()
    if playing2.hash != playing.hash:
        print('Content has changed')

Push updates
------------
The push update API is based on a regular callback interface. When playstatus
information is available, a method called ``playstatus_update`` is called.
Similarily, ``playstatus_error`` is called if an error occur. See the
following example:

.. code:: python

    class PushListener:

        def playstatus_update(self, updater, playstatus):
            # Currently playing in playstatus

        @staticmethod
        def playstatus_error(updater, exception):
            # Error in exception
            updater.start(initial_delay=10)


    @asyncio.coroutine
    def listen_to_updates(self);
        listener = PushListener()
        self.atv.push_updater.listener = listener
        self.atv.push_updater.start()

A few things worth noting:

- Both callback methods must be part of a "listener" (class)
- There can be only one listener
- If an error occurs, push updates are stopped

Think a bit extra about the last point. You must manually restart push updates
in case an error occur. The simplest way is to do like in the example above,
but make sure to provide an "initial delay" (in seconds). Otherwhise you
might end up in a loop where a push connection can never be established. This
might for instance happen if the device loses its IP-address.

When done, the async method ``stop`` must be called to not leak resources.
Unless push updates were stopped because an error occurred and never
restarted again.
