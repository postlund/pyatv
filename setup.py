#!/usr/bin/env python3
# encoding: utf-8

from pathlib import Path
from os.path import join, dirname
from setuptools import setup


def read(fname):
    """Read content of a file and return as a string."""
    return Path(join(dirname(__file__), fname)).read_text()


def get_requirements():
    """Retuen requirements with loose version restrictions."""
    return read("base_versions.txt").replace("==", ">=").split("\n")


setup(
    install_requires=get_requirements(),
)
