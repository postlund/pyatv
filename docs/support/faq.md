---
layout: template
title: FAQ
permalink: /support/faq/
link_group: support
---
# FAQ

This page tries to answer some common questions.

## General Questions

### Q1. My device is not found when scanning?

See [Troubleshooting](../troubleshooting/) for some hints on locating the issue.

### Q2. My Apple TV turns on every time I send a command with atvremote (it turns on my TV, receiver, etc). How do I disable that?

You can't. The device will turn itself on whenever a request is made to it
(and of course `atvremote` does that). It is how Apple has designed it. The only
thing you can do is to disable CEC so that your other devices doesn't wake up too.
That's about it.

### Q3. Is it possible to "see" if a device is turned on before sending a command?

No (there is at least no known way as of date).

### Q4. Why is all or some metadata missing when I am playing some media on my device?

Sometimes the Apple TV does not provide any metadata and in those cases there
is no metadata available. Unfortunately, there is nothing that can be done about
this. If you, however, can see for example a title or artwork in the
*Remote app* on your iPhone or iPad, then something is likely wrong. In this
case, you should write a bug report.

### Q5. Streaming with AirPlay does not work. It says "This AirPlay connection requires iOS 7.1 or later, OS X 10.10 or later, or iTunes 11.2 or later." on the screen. What's wrong?

The device authentication process has now been reversed engineered and implemented
in pyatv. In order to get rid of this message, you must perform AirPlay pairing with
the device and use the obtained credentials with playing media. See
[pairing with atvremote](../..//documentation/atvremote).

### Q6. When I scan, other devices like AirPlay speakers and iTunes libraries show up. Why is that?

~~Apple has re-used several protocols across different products. AirPlay is AirPlay and
there's no practical difference if it's on a speaker or an Apple TV: it's the same
thing. Because of this, they might show up in the scan results. In the future some
devices might be filtered (like pure AirPlay devices, since you can't connect to them
anyway), but for now they are there.~~

This is no longer the case. From `pyatv` 0.5.0, pure AirPlay devices are no longer included in the scan result.

## Technical Questions

### T1. Is there a synchronous version of the library?

No, the library is implemented with asyncio, introduced in python 3.4. A plain
synchronous library is currently out of scope and not a priority.

## Apps (tvOS)

Some apps behave in unexpected ways that are out of control of this library, i.e. nothing can be done in `pyatv` to circumvent these behaviors. This sections lists the known ones. If you are experiencing issues with an app, feel free to add it here (write an issue, make a PR or just press *Edit this page* at the bottom of this page).

### Netflix (com.netflix.Netflix)

* Previews in the main menu yields play status updates (usually with what was played most recently, not content of the preview). A workaround is to disable these previews, see [this](https://help.netflix.com/sv/node/2102) page.
* During episode intros and "next episode" screens the device goes to idle state.
* Sometimes the app name in {% include api i="interface.Metadata.app" %} is never set.

### playbackRate issue

Some apps incorrectly set the metadata item "playbackRate" as 0.0 instead of 1.0 which causes `pyatv` to report the media as paused at all times. A workaround for this issue has been pushed at [#673](https://github.com/postlund/pyatv/pull/673), seeking, fast-forwarding or rewinding will still return a "paused" state.

Apps known to cause this issue are listed below

* Amazon Prime Video (com.amazon.aiv.AIVApp)
* BBC iPlayer (uk.co.bbc.iplayer)


