#!/usr/bin/env python3
# encoding: utf-8

from setuptools import setup, find_packages

# Read in version without importing pyatv
# http://stackoverflow.com/questions/6357361/alternative-to-execfile-in-python-3
exec(compile(open('pyatv/const.py', "rb").read(), 'pyatv/const.py', 'exec'))

setup(
    name='pyatv',
    version=__version__,
    license='MIT',
    url='https://github.com/postlund/pyatv',
    author='Pierre Ståhl',
    author_email='pierre.staahl@gmail.com',
    description='Library for controlling an Apple TV',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'aiohttp>=1.3.5, <3',
        'cryptography>=1.8.1',
        'curve25519-donna>=1.3, <2',
        'ed25519>=1.4, <2',
        'srptools>=0.2.0',
        'zeroconf>=0.17.7'
    ],
    test_suite='tests',
    keywords=['apple', 'tv'],
    tests_require=['tox'],
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
        'Topic :: Home Automation',
    ],
)
