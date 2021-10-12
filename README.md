A client library for Apple TV and AirPlay devices
=================================================

<img src="https://raw.githubusercontent.com/postlund/pyatv/master/docs/assets/img/logo.svg?raw=true" width="150">

![Tests](https://github.com/postlund/pyatv/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/postlund/pyatv/branch/master/graph/badge.svg)](https://codecov.io/gh/postlund/pyatv)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPi Package](https://badge.fury.io/py/pyatv.svg)](https://badge.fury.io/py/pyatv)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/postlund/pyatv.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/postlund/pyatv/context:python)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/postlund/pyatv)
[![Downloads](https://pepy.tech/badge/pyatv)](https://pepy.tech/project/pyatv)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pyatv.svg)](https://pypi.python.org/pypi/pyatv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This is an asyncio python library for interacting with Apple TV and AirPlay devices. It mainly
targets Apple TVs (all generations, **including tvOS 15**), but also support audio streaming via AirPlay to
receivers like the HomePod, AirPort Express and third-party speakers. It can act as remote control to the Music
app/iTunes in macOS.

All the documentation you need is available at **[pyatv.dev](https://pyatv.dev)**.

# What can it do?

Some examples include:

* Remote control commands
* Metadata retrieval with push updates
* Stream files via AirPlay
* List and launch installed apps

...and lots more! A complete list is available [here](https://pyatv.dev/documentation/supported_features/).

# Great, but how do I use it?

All documentation (especially for developers) are available at [pyatv.dev](https://pyatv.dev).
It is however possible to install with `pip` and try things out with `atvremote`:

```raw
$ pip install pyatv
$ atvremote scan
       Name: Office
   Model/SW: HomePodMini tvOS 14.7
    Address: 10.0.10.84
        MAC: AA:BB:CC:DD:EE:FF
 Deep Sleep: False
Identifiers:
 - AA:BB:CC:DD:EE:FF
 - AABBCCDDEEFF
Services:
 - Protocol: AirPlay, Port: 7000, Credentials: None
 - Protocol: Companion, Port: 49152, Credentials: None
 - Protocol: RAOP, Port: 7000, Credentials: None, Password: None
```

Or run in a container (x86_64, aarch64, armv7):

```raw
docker run -it --rm --network=host ghcr.io/postlund/pyatv:master atvremote scan
```

The `master` tag points to latest commit on the `master` branch and can
be changed to a specific version, e.g. `v0.9.0`.

# I need to change something?

Want to help out with `pyatv`? Press the button below to get a fully prepared development environment and get started right away!

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/postlund/pyatv)

# Shortcuts to the good stuff

To save you some time, here are some shortcuts:

* [Getting started](https://pyatv.dev/documentation/getting-started/)
* [Documentation](https://pyatv.dev/documentation)
* [Development](https://pyatv.dev/development)
* [API Reference](https://pyatv.dev/api)
* [Support](https://pyatv.dev/support)
