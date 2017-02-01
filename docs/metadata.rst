.. _pyatv-metadata:

Fetching metadata
=================
Retrieving metadata from the device works very similar to the remote control
API, but one asynchronous call will return an object containing the metadata
to lower the amount of calls needed. Artwork is retrieved separately.

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