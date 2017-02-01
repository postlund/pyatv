.. _pyatv-faq:

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