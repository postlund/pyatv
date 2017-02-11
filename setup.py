#!/usr/bin/env python3
# encoding: utf-8

from setuptools import setup, find_packages

setup(
    name='pyatv',
    version='0.1.4',
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
        'aiohttp==1.3.1',
        'zeroconf==0.18.0',
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
        'Topic :: Software Development :: Libraries',
        'Topic :: Home Automation',
    ],
)
