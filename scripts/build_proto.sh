#!/bin/bash

if [ ! -e "setup.py" ]; then
    >&2 echo "Run this script from pyatv root directory (where setup.py is)!"
    exit 1
fi

protoc --proto_path=. --python_out=. pyatv/mrp/protobuf/*.proto
