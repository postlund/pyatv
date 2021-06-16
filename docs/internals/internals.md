---
layout: template
title: Internals
permalink: /internals/
link_group: internals
---
# :microscope: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Internals

Welcome to the developer documentation for pyatv, i.e. the documentation explaining how
pyatv works (internally) and how to extend it. This section used to reside in the
GitHub wiki, but has moved to the general documentation for greater availability. It is
still under heavy development, so beware of missing and/or outdated content as it is
migrated from the wiki.

# Setting up a New Environment

## Linux/macOS/*NIX

You can run the script `scripts/setup_dev_env.sh` to set up a complete development environment. It will make sure that everything works as expected by running `tox`, building documentation (with docker), etc.

```shell
$ ./scripts/setup_dev_env.sh
```

## Windows

There's no helper script for windows, but you can get started manually like this:

```shell
$ git clone https://github.com/postlund/pyatv.git
$ cd pyatv
$ python3 -m venv venv
$ source venv/Scripts/activate
$ python setup.py develop
$ pip install tox
$ pip install -r requirements_test.txt
$ tox
```

# Testing Changes

If you followed the instructions above, then pyatv will be installed as "develop". This means that you can keep doing updates without having to do `python setup.py install` between changes.

## Testing with tox

To test everything, just run `tox`:

```shell
$ tox -p auto
```

This will make sure that tests pass, you have followed coding guidelines (pylint, flake8, etc), verify protobuf messages and generate coverage data. You can run steps individually as well:

| What | Command |
| ---- | ------- |
| Unit tests | tox -e py{35,36,37,38}
| Code style | tox -e codestyle
| pylint | tox -e pylint
| Generated Code | tox -e generated
| Documentation | tox -e docs

*Note: `pylint` should technically be part of `codestyle` but has been extracted to its own
environment to increase parallelization.*

If you change required version for, add or remove a dependency you should pass `-r` to `tox`
to force it to re-create the environment (once). Otherwise your changes will not be reflected.

Generally, `tox` will install the latest version of all dependencies when setting up new
environments. There's however a special environment called `regression`, which will install
the "lowest versions" of all dependencies (that pyatv is supposed to work with) and run
checks with those. Generally you will not need to run that by yourself, but sometimes you
might find that it breaks when GitHub Actions runs it.

Base versions used by `regression` are in {% include code file="../base_versions.txt" %}.

## Updating protobuf Definitions

If you have made changes to the protobuf messages in `pyatv/mrp/protobuf`, you can make sure everything is updated by running:

```shell
$ ./scripts/protobuf.py --download generate
```

See [Protobuf](tools#protobuf) for more details.

## Running Tests

Recommended way to run unit tests:

```shell
$ pytest --log-level=debug --disable-warnings
```

Warnings are disabled because of deprecated `loop` argument in lots of places. This flag will be lifted eventually. See [Testing](testing) for details regarding tests.

## Re-formatting code

All python code is formatted using [black](https://github.com/psf/black), so you don't have to care about how the code looks. Just let black take care of it:

```shell
$ black .
All done! ✨ 🍰 ✨
77 files left unchanged.
```

Code formatting is checked by `tox`, so it's not possible to check in code if it doesn't comply with black.

## Documentation

**NB: This step currently requires docker and is only tested on Linux!**

To serve a local running web server that performs incremental updates of the documentation,
run:

```shell
$ ./scripts/build_doc.sh
```

Navigate to [http://localhost:4000](http://localhost:4000) to see the result.

The `lint` environment (`tox -e lint`) will do basic spell checking of the documentation (and code) using [codespell](https://github.com/codespell-project/codespell).

# Cheat Sheet

Here are a few convenient commands in short form:

| Command | What
| ------- | ----
| pytest --disable-warnings --log-level=debug -k XXX | Run tests matching XXX
| black . | Re-format code with black
| ./scripts/protobuf.py --download generate | Update protobuf definitions
| ./scripts/build_doc.sh | Serve web server with documentation at [http://127.0.0.1:4000](http://127.0.0.1:4000)
| ./scripts/api.sh generate | Update generate API `documentation in docs/api`
| ./scripts/features.sh | Generate `pyatv.const.FeatureName` (you need to copy-paste it) and print next free index
