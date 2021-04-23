#!/bin/bash

PYTHON="python3.8 python3.7 python3.6"

found_version=
for p in $PYTHON
do
    which $p 2>&1 > /dev/null
    if [ $? -eq 0 ]; then
        found_version=$p
        break
    fi
done

set -e

if [ -z $found_version ]; then
    >&2 echo "no python installation found"
    exit 1
fi

echo "-> Using python: $found_version"

echo "-> Creating python virtual environment..."
$found_version -m venv .

echo "-> Activating virtual environment..."
source bin/activate
sed -i 's/false/true/' pyvenv.cfg

echo "-> Upgrading pip..."
pip install --upgrade pip

echo "-> Installing library as develop..."
python setup.py develop

echo "-> Installing protobuf-setuptools..."
pip install protobuf-setuptools

echo "-> Installing test dependencies..."
pip install -r requirements_test.txt
pip install tox

echo "-> Running tests as verification..."
python setup.py test

echo "-> Generating documentation..."
./scripts/build_docs.sh build


cat <<EOF
==================================================

When starting a new shell, run:

  source bin/activate

To run tests, run any of:

  python setup.py test
  pytest tests/test_conf.py  # Single test

To re-generate protobuf messages:

  ./scripts/build_proto.sh
  ./scripts/autogen_protobuf_extensions.py > pyatv/mrp/protobuf/__init__.py

The CLI application can be used, e.g. run:

  atvremote --debug commands
  atvremote --developer --debug playing

To preview documentation in docs, run:

  ./scripts/build_docs.sh serve

and navigate to http://127.0.0.1:4000

==================================================

Environment is configured and ready to use!
EOF
