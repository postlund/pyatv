---
layout: template
title: Documentation
permalink: /documentation/
link_group: documentation
---
# Documentation

This section covers general parts of `pyatv`, like how to install it, concepts and terminology to
understand how it works. More or less everything that is not *how* you develop with it.

Before diving into code, make sure you read and understand the [Concepts](documentation/concepts/)
first.

## Installing pyatv

To install `pyatv`, just use `pip`:

    pip install {{ site.pyatv_version }}

You might need some additional packages to compile the dependencies. On a debian based system
(e.g. Debian itself or Ubuntu), you can just run:

    sudo apt-get install build-essential libssl-dev libffi-dev python-dev

### Development version

To try out the latest development version (a.k.a. `master` on GitHub), you can install with:

    pip install git+https://github.com/postlund/pyatv.git

### Dependencies

To get the work done, `pyatv` requires some other pieces of software, more specifically:

- python >= 3.5.3
- aiohttp >= 3.0.1, <4
- aiozeroconf >= 0.1.8
- cryptography >= 1.8.1
- curve25519-donna >= 1.3
- ed25519 >= 1.4
- netifaces >= 0.10.0
- protobuf >= 3.4.0
- srptools >= 0.2.0
- tlslite-ng >= 0.7.0

### Roadmap

Current roadmap is available on GitHub:

**[Roadmap](https://github.com/postlund/pyatv/milestones)**
