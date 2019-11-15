---
layout: template
title: FAQ
permalink: /support/faq/
link_group: support
---
# FAQ

This page tries to answer some common questions.

## General Questions

### My device is not found when scanning?

See [Troubleshooting](support/troubleshooting/) for some hints on locating the issue.

### Why is all or some metadata missing when I am playing some media on my device?

Sometimes the Apple TV does not provide any metadata and in those cases there
is no metadata available. Unfortunately, there is nothing that can be done about
this. If you, however, can see for example a title or artwork in the
*Remote app* on your iPhone or iPad, then something is likely wrong. In this
case, you should write a bug report.

### Streaming with AirPlay does not work. It says "This AirPlay connection requires iOS 7.1 or later, OS X 10.10 or later, or iTunes 11.2 or later." on the screen. What's wrong?

The device authentication process has now been reversed engineered and implemented
in pyatv. In order to get rid of this message, you must perform AirPlay pairing with
the device and use the obtained credentials with playing media. See
[pairing with atvremote](documentation/atvremote).

## Technical Questions

### Is there a synchronous version of the library?

No, the library is implemented with asyncio, introduced in python 3.4. A plain
synchronous library is currently out of scope and not a priority.
