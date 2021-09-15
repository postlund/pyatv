---
layout: template
title: pyatv
---
# :tv: Main Page

This is an asyncio python library for interacting with Apple TV and AirPlay devices. It mainly
targets Apple TVs (all generations), but also support audio streaming via AirPlay to receivers like the HomePod,
AirPort Express and third-party speakers. It can act as remote control to the Music app/iTunes in macOS.

![Tests](https://github.com/postlund/pyatv/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/postlund/pyatv/branch/master/graph/badge.svg)](https://codecov.io/gh/postlund/pyatv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPi Package](https://badge.fury.io/py/pyatv.svg)](https://badge.fury.io/py/pyatv)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/postlund/pyatv.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/postlund/pyatv/context:python)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/postlund/pyatv)
[![Downloads](https://pepy.tech/badge/pyatv)](https://pepy.tech/project/pyatv)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pyatv.svg)](https://pypi.python.org/pypi/pyatv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# :satisfied: Features

Here is a short summary of supported features:

* Automatic device discovery with Zeroconf
* Device information, e.g. hardware model and operating system version
* Currently playing metadata, artwork and push updates
* Remote, navigation and volume control commands
* Basic support for streaming video and audio with AirPlay
* Listing installed apps, launching apps and currently playing app
* Power management, e.g. turn on or off
* Supports Apple TV (all of them), AirPort Express, HomePod, macOS music app and most AirPlay v1 receivers

A complete list of supported features and limitations is available
[here](documentation/supported_features).

There are also few utility scripts bundled with pyatv that makes it easy to try the library
out. Check out [atvremote](documentation/atvremote), [atvproxy](documentation/atvproxy),
[atvscript](documentation/atvscript) and [atvlog](documentation/atvlog).

# :eyes: Where to start?

To get going, install with `pip`:

<div class="center_box" style="margin-bottom: 2em">
  <p style="margin: 0px">:tada: <a href="https://pypi.org/project/pyatv">pip install pyatv :tada:</a></p>
</div>

Head over to [Getting started](documentation/getting-started) to see what you can do! There's
also a [Tutorial](documentation/tutorial) if you want to get going faster!

As pyatv is a library, it is mainly aimed for developers creating applications that can interact
with Apple TVs. However, pyatv ships with a few powerful command lines tools you can use to
try the library without writing any code.

If you need help or have questions, check out the [Support](support) page instead.

In case you are upgrading from an earlier version of pyatv, make sure to check out the migration
guide [here](support/migration) that will help you port your existing code.

# :cloud: In other the news...

As pyatv depends solely on private and reverse engineered protocols, things sometimes break because
Apple changes something. Or because of other reasons. This section covers the major things that you
need to be aware of.

* Apple removed the "regular" MRP protocol in tvOS 15 and started tunneling it over AirPlay instead.
  Version 0.9.0 of pyatv is the first version supporting tvOS 15. As long as credentials are provided
  for AirPlay, everything should be seamless, i.e. nothing more needs to be done. Credentials obtained
  from earlier versions will not work however, pairing must be re-performed with 0.9.0 (or later).
* Playing anything with {% include api i="interface.Stream.play_url" %} tends to break devices running
  tvOS, e.g. metadata stops working. Rebooting is the only recovery. Everything points at a bug in
  tvOS.
* It is possible to control the Music app running on a Mac, but macOS 11.4 seems to not work. Make
  sure to upgrade.
* There are some issues with {% include pypi package="miniaudio" %} when running on ARM
  (e.g. Rasperry pi) which can be fixed by re-installing {% include pypi package="miniaudio" %} and
  building it from source. See [here](support/faq#when-using-pyatv-on-a-raspberry-pi-eg-running-atvremote-i-get-illegal-instruction-how-do-i-fix-that)
  for details.
* {% include pypi package="miniaudio" %} fails to compile on Apple Silicon {% include issue no="1162" %}
* Other general issues can be found in the [FAQ](support/faq).

# :trophy: Who uses pyatv?

Here are a few projects known to use pyatv:

* [Home Assistant](https://home-assistant.io) - The Apple TV integration is powered by pyatv

If you are maintaining a project using pyatv, feel free to add it to the list (open a PR
or [issue](https://github.com/postlund/pyatv/issues/new?assignees=&labels=question,documentation&template=question-or-idea.md&title=Add+my+pyatv+project+to+list&assignees=postlund)).
You don't need to provide a URL if you don't want, just a short description of the use case
is fine too!

# :office: License

This library is licensed under the
[MIT license](https://github.com/postlund/pyatv/blob/master/LICENSE.md).

# :person_with_blond_hair: Who is making this?

I, Pierre Ståhl, is the lead developer and maintainer of this library. It is a hobby
project that I put a few hours in every now and then to maintain. If you find it useful,
please consider to sponsor me! :heart:

Of course, this is an open source project which means I couldn't do it all by myself.
I have created dedicated page for [acknowledgements](support/acknowledgements)!
