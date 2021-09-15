---
layout: template
title: Documentation
permalink: /documentation/
link_group: documentation
---
# :green_book: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Documentation

This section covers general parts of pyatv, like how to install it, concepts and terminology to
understand how it works. More or less everything that is not *how* you develop with it.

Before diving into code, make sure you read and understand the [Concepts](concepts/)
first.

# Installing pyatv

You can install/run pyatv either in a container using pre-built images or a virtual environment.

## Container (Docker)

Starting with release 0.9.0, container images for x86_64, aarch64 and armv7 are automatically built and
available from GitHub. Images are published per version (e.g. v0.9.0, v0.9.1, etc.) and the latest
commit on `master` (just labeled with `latest`). See the [images](https://github.com/postlund/pyatv/pkgs/container/pyatv)
page for all available images.

To test atvremote, you can run:

```shell
$ docker run -it --rm --network=host ghcr.io/postlund/pyatv:master atvremote scan
```

It is also possible to run simple scripts and applications like this:

```shell
$ docker run --rm --network=host -v $PWD:/app ghcr.io/postlund/pyatv:v0.9.0 python /app/scan.py
```

Note that network must be used in `host` mode, otherwise pyatv will not be able to find your
devices when scanning.

## Virtual Environment

It is recommended to install pyatv in a virtual environment rather than
system-wide. To create a new virtual environment:

    python3 -m venv pyatv_venv
    source pyatv_venv/bin/activate

This creates a virtual environment in a directory called `pyatv_venv`. The
second command activates the virtual environment and must be done every
time a new shell is started.

You might need some additional packages to compile the dependencies. On a debian based system
(e.g. Debian itself or Ubuntu), you can just run:

```shell
sudo apt-get install build-essential libssl-dev libffi-dev python-dev
```

Now you can continue by installing the version of pyatv you want.

### Latest Stable Version

Install pyatv using `pip3`:

```shell
pip3 install {{ site.pyatv_version }}
```

### Development Version

To try out the latest development version (a.k.a. `master` on GitHub), you can install with:

```shell
pip3 install --upgrade git+https://github.com/postlund/pyatv.git
```

### Specific Branch or a Pull Request

To install from a branch, you can install like this:

```shell
pip3 install --upgrade git+https://github.com/postlund/pyatv.git@refs/heads/<branch>
```

Replace `<branch>` with the name of the branch.

It is also possible to install directly from a pull request:

```shell
pip3 install git+https://github.com/postlund/pyatv.git@refs/pull/<id>/head
```

Replace `<id>` with the pull request number.

# Testing with GitPod

You can try out pyatv and play around with the code using GitPod. Everything is
already set up and ready to go, just login with one of the supported account,
e.g. GitHub, and you are ready within a minute. No need to install anything on
your own computer and works across operating systems and web browsers. Really cool!

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/postlund/pyatv)

*Note: This runs in the cloud, so you will not be able to find your own devices. It's mainly for development or basic testing.*

# Dependencies

At least python 3.6 is required to run pyatv. A few additional libraries
are needed as well. An updated list is available
[here](https://github.com/postlund/pyatv/blob/master/base_versions.txt).

You also need to have OpenSSL compiled with support for ed25519 in order
to connect to MRP devices. More details is
[here](../support/faq/#i-get-an-error-about-ed25519-is-not-supported-how-can-i-fix-that).

# Milestones

Current milestones are available on GitHub:

[Milestones](https://github.com/postlund/pyatv/milestones)
