#!/usr/bin/env python3
# encoding: utf-8

import os
from setuptools import setup, find_packages

# Read in version without importing pyatv
# http://stackoverflow.com/questions/6357361/alternative-to-execfile-in-python-3
exec(compile(open('pyatv/const.py', "rb").read(), 'pyatv/const.py', 'exec'))


# Read content of a file and return as a string
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='pyatv',
    version=__version__,
    license='MIT',
    url='https://github.com/postlund/pyatv',
    author='Pierre Ståhl',
    author_email='pierre.staahl@gmail.com',
    description='Library for controlling an Apple TV',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'aiohttp>=3.0.1, <4',
        'aiozeroconf>=0.1.8',
        'cryptography>=1.8.1',
        'curve25519-donna>=1.3',
        'ed25519>=1.4',
        'netifaces>=0.10.0',
        'protobuf>=3.8.0',
        'srptools>=0.2.0',
        'tlslite-ng>=0.7.0',
    ],
    test_suite='tests',
    keywords=['apple', 'tv'],
    setup_requires=['pytest-runner'],
    tests_require=['tox', 'pytest==5.3.5', 'pytest-xdist==1.31.0'],
    entry_points={
        'console_scripts': [
            'atvremote = pyatv.__main__:main'
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries',
        'Topic :: Home Automation',
    ],
)
