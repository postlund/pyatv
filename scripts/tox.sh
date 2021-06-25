#!/bin/bash

# This script is supposed to be run by GitHub actions. It will
# re-run tox with pip cache disabled in case of error.
tox -q -p auto || PIP_ARGS="--no-cache-dir" tox -q -p auto
