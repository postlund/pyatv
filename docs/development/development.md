---
layout: template
title: Development
permalink: /development/
link_group: development
---
# Development

These sections cover the basics on how you develop with `pyatv`. So if you are a developer
and want to create some software that controls an Apple TV, you are in the right place.

This page mainly cover the basics on extending `pyatv`. If you intend to just use `pyatv`
as a library, skip to the subpages. If you feel that some information is missing, please write
a [request](https://github.com/postlund/pyatv/issues/new?assignees=&labels=feature&template=feature_request.md&title=) for clarification.

## Setting up a development environment

Fork this project, clone it and run `setup_dev_env.sh` to setup a virtual environment and
install everything needed for development:

    git clone https://github.com/postlund/pyatv.git
    cd pyatv
    ./scripts/setup_dev_env.sh
    source bin/activate

When using atvremote, pass `--debug` to get better logging.

## Running tests, linting, etc.

This project uses `tox` to verify that all tests pass across various versions of
python. It also verifies things like code style and typing. You can just run `tox`
in the repository main directory to see if everything is OK. When pushing code to GitHub,
these checks are run automatically and code will not merge if there are any errors.

To just run the tests, just call `pytest` manually:

    pytest tests/

The same thing works for e.g. `pylint` and `flake8` as well:

    pylint pyatv
    flake8 pyatv
