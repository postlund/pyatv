#!/usr/bin/env python3
# encoding: utf-8

from pathlib import Path
from os.path import join, dirname
from setuptools import setup, find_packages

GITHUB_URL = "https://github.com/postlund/pyatv"

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
    url="https://pyatv.dev",
    download_url=f"{GITHUB_URL}/archive/refs/tags/v{__version__}.zip",
    project_urls={
        "Repository": GITHUB_URL,
        "Bug Reports": f"{GITHUB_URL}/issues"
    },
    author="Pierre Ståhl",
    author_email="pierre.staahl@gmail.com",
    description="A client library for Apple TV and AirPlay devices",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests", "tests.*", "examples"]),
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=get_requirements(),
    test_suite="tests",
    keywords=["apple", "tv", "airplay", "raop", "companion", "dmap", "dacp"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest==6.2.5", "pytest-xdist==2.4.0"],
    python_requires=">=3.9.0",
    entry_points={
        "console_scripts": [
            "atvremote = pyatv.scripts.atvremote:main",
            "atvproxy = pyatv.scripts.atvproxy:main",
            "atvscript = pyatv.scripts.atvscript:main",
            "atvlog = pyatv.scripts.atvlog:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries",
        "Topic :: Home Automation",
        "Typing :: Typed",
    ],
)
