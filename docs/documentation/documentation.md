---
layout: template
title: Documentation
permalink: /documentation/
link_group: documentation
---
# Documentation

This section covers general parts of `pyatv`, like how to install it, concepts and terminology to
understand how it works. More or less everything that is not *how* you develop with it.

Before diving into code, make sure you read and understand the [Concepts](concepts/)
first.

## Installing pyatv

It is recommended to install `pyatv` in a virtual environment rather than
system-wide. To create a new virtual environment:

    python3 -m venv pyatv_venv
    source pyatv_venv/bin/activate

This creates a virtual environment in a directory called `pyatv_venv`. The
second command activates the virtual environment and must be done every
time a new shell is started.

You might need some additional packages to compile the dependencies. On a debian based system
(e.g. Debian itself or Ubuntu), you can just run:

    sudo apt-get install build-essential libssl-dev libffi-dev python-dev

Now you can continue by installing the version of `pyatv` you want.

### Latest Stable Version

Install `pyatv` using `pip3`:

    pip3 install {{ site.pyatv_version }}

#### Development Version

To try out the latest development version (a.k.a. `master` on GitHub), you can install with:

    pip3 install --upgrade git+https://github.com/postlund/pyatv.git

#### Specific Branch or a Pull Request

To install from a branch, you can install like this:

    pip3 install --upgrade git+https://github.com/postlund/pyatv.git@refs/heads/<branch>

Replace `<branch>` with the name of the branch.

It is also possible to install directly from a pull request:

    pip3 install git+https://github.com/postlund/pyatv.git@refs/pull/<id>/head

Replace `<id>` with the pull request number.

### Dependencies

To get the work done, `pyatv` requires some other pieces of software, more specifically:

- python >= 3.6.0
- aiohttp >= 3.1.0, <5
- cryptography >= 2.6
- netifaces >= 0.10.0
- protobuf >= 3.6.0
- srptools >= 0.2.0
- zeroconf==0.28.0

You also need to have OpenSSL compiled with support for ed25519 in order
to connect to MRP devices.

### Milestones

Current milestones are available on GitHub:

**[Milestones](https://github.com/postlund/pyatv/milestones)**
