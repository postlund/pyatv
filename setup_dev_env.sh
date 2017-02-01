#!/bin/bash

PYTHON="python3.5 python3.4"

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
virtualenv -p $found_version .

echo "-> Activating virtual environment..."
source bin/activate

echo "-> Upgrading pip..."
pip install --upgrade pip

echo "-> Installing library as develop..."
python setup.py develop

echo "-> Installing test dependencies..."
pip install -r requirements_test.txt
pip install tox

echo "-> Running tests as verification..."
python setup.py test

echo "-> Generating documentation..."
cd docs && make html


cat <<EOF
==================================================

When starting a new shell, run:

  source bin/activate

To run tests, run:

  python setup.py test

The CLI application can be used, e.g. run:

  atvremote --debug -a commands
  atvremote --developer --debug -a dev_playstatus

HTML documentation has been generated in:

  docs/generated/html

To re-generate documentation, e.g. run:

  make -C docs html

==================================================

Environment is configured and ready to use!
EOF
