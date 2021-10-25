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

You can run the script `scripts/setup_dev_env.sh` to set up a complete development environment. It will make sure that everything works as expected by running `chickn`, building documentation (with docker), etc.

```shell
$ ./scripts/setup_dev_env.sh
$ ./scripts/chickn.py
```

## Windows

There's no helper script for windows, but you can get started manually like this:

```shell
$ git clone https://github.com/postlund/pyatv.git
$ cd pyatv
$ python3 -m venv venv
$ source venv/Scripts/activate
$ python setup.py develop
$ pip install pyyaml -r requirements/requirements_test.txt -r requirements/requirements_docs.txt
$ python scripts/chickn.py
```

# Testing Changes

If you followed the instructions above, then pyatv will be installed as "develop". This means that you can keep doing updates without having to do `python setup.py install` between changes.

## Testing with chickn

To test everything, just run `./scripts/chickn.py`:

```shell
$ ./scripts/chickn.py
```

This will make sure that tests pass, you have followed coding guidelines (pylint, flake8, etc), verify protobuf messages and generate coverage data. `chickn` is developed for pyatv and the documentation for it is
[here](tools/#chickn). The configuration file is [here](https://github.com/postlund/pyatv/blob/master/pyatv/chickn.yaml)

You can run steps individually as well:

| What | Command |
| ---- | ------- |
| tests | ./scripts/chickn.py pytest
| pylint | ./scripts/chickn.py pylint
| protobuf | ./scripts/chickn.py protobuf
| api | ./scripts/chickn.py api

All available steps can be listed with `./scripts/chickn.py -l`:

```raw
$ ./scripts/chickn.py -l
clean, fixup, pylint, api, protobuf, flake8, black, pydocstyle, isort, cs_docs, cs_code, typing, pytest, report, dist
```

The `fixup` will run black and isort to clean up basic mistakes before running rest of the commands.
So it can be convenient to enable that step with the `fixup` tag:

```raw
./scripts/chickn.py -t fixup
```

Generally, `chickn` will install the latest version of all dependencies. There's however a
wish to verify that everything works the lowest version that pyatv supports. This is denoted
as "regression" in GitHub actions. These versions are listed in {% include code file="../base_versions.txt" %}
and can be manually overridden when needed:

```raw
$ ./scripts/chickn.py -v requirements_file=base_versions.txt
2021-10-24 11:16:19 [INFO] Installing dependencies
2021-10-24 11:16:19 [INFO] Re-installing packages with mismatching versions: aiohttp==3.1.0 (3.7.4), bitarray==2.1.2 (2.3.4), cryptography==2.6 (35.0.0), netifaces==0.10.0 (0.11.0), protobuf==3.18.0 (3.19.0), srptools==0.2.0 (1.0.1), zeroconf==0.28.2 (0.36.8)
...
```

You generally do not need to do this yourself as it is tested automatically by GitHub Actions.

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
$ ./scripts/chickn.py pytests  # Can be run via chickn
```

Warnings are disabled because of deprecated `loop` argument in lots of places. This flag will be lifted eventually. See [Testing](testing) for details regarding tests.

## Re-formatting code

All python code is formatted using [black](https://github.com/psf/black), so you don't have to care about how the code looks. Just let black take care of it:

```shell
$ black .
All done! ✨ 🍰 ✨
77 files left unchanged.
```

Code formatting is checked by `chickn`, so it's not possible to check in code if it doesn't comply with black.

## Documentation

**NB: This step currently requires docker and is only tested on Linux!**

To serve a local running web server that performs incremental updates of the documentation,
run:

```shell
$ ./scripts/build_doc.sh
```

Navigate to [http://localhost:4000](http://localhost:4000) to see the result.

The `cs_docs` step (`./scripts/chickn.py cs_docs`) will do basic spell checking of the documentation
using [codespell](https://github.com/codespell-project/codespell).

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
