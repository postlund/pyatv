.. _pyatv-faq:

.. role:: strike
    :class: strike

FAQ
===
This page tries to answer some common questions.

General Questions
-----------------
**Why is all or some metadata missing when I am playing some media on my
device?**

Sometimes the Apple TV does not provide any metadata and in those cases there
is no metadata available. Unfortunately, there is nothing that can be done about
this. If you, however, can see for example a title or artwork in the
*Remote app* on your iPhone or iPad, then something is likely wrong. In this
case, you should write a bug report.

**When using Plex on Apple TV 4, pause and previtem does not work as expected. Is
this a bug in pyatv?**

This seems to be an issue with Plex, or rather bug in the media player (AVPlayer).
You can read more about it in `issue #7 <https://github.com/postlund/pyatv/issues/7>`_
on GitHub and `here <https://forums.plex.tv/discussion/191765/fast-forward-and-rewind-problem>`_.
Unfortunately, this is not something pyatv can fix or work around. We'll just
have to sit tight and wait for a fix in tvOS.

**Streaming with AirPlay does not work. It says "This AirPlay connection requires
iOS 7.1 or later, OS X 10.10 or later, or iTunes 11.2 or later." on the screen.
What's wrong?**

The device authentication process has now been reversed engineered and implemented
in pyatv. In order to get rid of this message, you must perform *device authentication*.
If you are interested in development details (like the API), check out
:ref:`the AirPlay page<pyatv-airplay>`. To try it out with ``atvremote``, instead
check out the section about it at :ref:`atvremote<pyatv-atvremote>`.

:strike:`From tvOS 10.2 and later, Apple enforces "device verification". This was optional
and disabled by default in earlier versions. After this update, a lot of 3rd party
tools broke, including pyatv. This means that it is currently not possible to stream
content to an Apple TV running tvOS 10.2 (or later). As soon as the device
verification scheme has been reversed engineered, support will be added. But there
is no timeframe for this.`

Technical Questions
-------------------
**Is there a synchronous version of the library?**

No, the library is implemented with asyncio, introduced in python 3.4. A plain
synchronous library is currently out of scope and not a priority.

**Why not use the async/await syntax introduced in python 3.5?**

Mainly for greater compatibility. It is now also supported in python 3.4. Since
the main driver for this library was support for the Apple TV in
`Home-Assistant <https://home-assistant.io/>`_, it was natural to pick the
older version (since Home Assistant is implemented in that).
