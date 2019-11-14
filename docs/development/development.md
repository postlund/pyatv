---
layout: template
title: Development
permalink: /development/
link_group: development
---
# Development

TBD

## Setting up a development environment

Fork this project, clone it and run `setup_dev_env.sh` to setup a virtual environment and
install everything needed for development:

    git clone https://github.com/postlund/pyatv.git
    cd pyatv
    ./scripts/setup_dev_env.sh
    source bin/activate

You can run the tests with `python setup.py test`. Also, make sure that `pylint`, `flake8` and
`pydoc` passes before committing. This is done automatically if you run just run `tox`.

When using atvremote, pass `--debug` to get better logging.
