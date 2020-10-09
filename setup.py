#!/usr/bin/env python3
# encoding: utf-8

from pathlib import Path
from os.path import join, dirname
from setuptools import setup, find_packages

# Read in version without importing pyatv
# http://stackoverflow.com/questions/6357361/alternative-to-execfile-in-python-3
exec(compile(open("pyatv/const.py", "rb").read(), "pyatv/const.py", "exec"))


def read(fname):
    """Read content of a file and return as a string."""
    return Path(join(dirname(__file__), fname)).read_text()


def get_requirements():
    """Retuen requirements with loose version restrictions."""
    return read("base_versions.txt").replace("==", ">=").split("\n")


setup(
    name="pyatv",
    version=__version__,
    license="MIT",
    url="https://github.com/postlund/pyatv",
    author="Pierre Ståhl",
    author_email="pierre.staahl@gmail.com",
    description="Library for controlling an Apple TV",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=get_requirements(),
    test_suite="tests",
    keywords=["apple", "tv"],
    setup_requires=["pytest-runner"],
    tests_require=["tox==3.20.1", "pytest==6.1.1", "pytest-xdist==2.1.0"],
    entry_points={
        "console_scripts": [
            "atvremote = pyatv.scripts.atvremote:main",
            "atvproxy = pyatv.scripts.atvproxy:main",
            "atvscript = pyatv.scripts.atvscript:main"
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Libraries",
        "Topic :: Home Automation",
    ],
)
