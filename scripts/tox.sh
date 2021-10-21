#!/bin/bash

if [ "$1" == "regression" ]; then
    echo "* Regression mode"
    base_versions=base_versions
else
    echo "* Normal mode"
    base_versions=base_versions2
fi

pip install --upgrade -r ${base_versions}.txt -r requirements_test.txt -r requirements_docs.txt

tox -vv --current-env --no-provision -q -p auto
