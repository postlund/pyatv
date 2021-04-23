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

echo "-> Installing dependencies..."
pip install --upgrade -r requirements_test.txt -r requirements_docs.txt
pip install tox

if [[ $GITPOD_INSTANCE_ID ]]; then
  echo "> Re-installing netifaces in GitPod due to bug"
  pip uninstall -y netifaces
  pip install netifaces
fi

echo "-> Running tests as verification..."
python setup.py test

cat <<EOF
==================================================

When starting a new shell, run:

  source bin/activate

To run tests, run any of:

  python setup.py test
  pytest tests/test_conf.py  # Single test

Test everything with tox:

  tox -p auto

To re-generate protobuf messages:

  ./scripts/protobuf.py --download generate

The CLI application can be used, e.g. run:

  atvremote --debug commands
  atvremote --debug playing

To preview documentation in docs, run:

  ./scripts/build_docs.sh

and navigate to http://127.0.0.1:4000

==================================================

Environment is configured and ready to use!
EOF
