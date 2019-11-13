.. _pyatv-developing:

Developing pyatv
================
If you feel that you want to help improving pyatv, this is the page for you.

Development environment
-----------------------
It is extremely simple to get started: fork the project on GitHub, clone it
and run the bundled script:

.. code:: bash

    git clone https://github.com/postlund/pyatv.git
    cd pyatv
    ./setup_dev_env.sh
    source bin/activate

You need ``virtualenv`` and python development package installed. On debian
or debian based distros (e.g. Ubuntu or raspian), you can just run the
following *before* running ``setup_dev_env.sh``:

.. code:: bash

    sudo apt-get install virtualenv python3-dev

The included script ``setup_dev_env.sh`` will automatically do the following
tasks:

* Create a python virtual environment
* Install the library as "develop"
* Install all dependencies and required tools
* Ensure that tests work by running tox
* Generate (this) documentation with sphinx

Once everything is done, all you have to do is to ensure that you are in the
virtual environment (``source bin/activate``).

.. note::

    As a library, pyatv should be platform independent, but it has only been
    verified to work on Linux and macOS. The same goes for this helper script.
    Support on Windows in particular is not guaranteed. Feel free to improve
    on this.

Running the tests
-----------------
You can run the tests either using ``setuptools`` or by using tox:

.. code:: bash

    python setup.py test

    OR

    tox -e py35  # python 3.5

When running with tox, you will also get code coverage. The report will be
written to a directory called ``htmlcov``.

Linting
-------
To ensure good code quality, the following tools are used:

* flake8 - verifies that code follows code standard
* pylint - performs code analysis
* pydocstyle - checks documentation strings

Use tox to easily check everything:

.. code:: bash

    tox -e lint

Requirements for pull requests
------------------------------
For a pull request to get merged, the following must be met:

* Tests for new functionality or bug fixes
* All tests must pass
* Do not decrease code coverage
* Include pydoc and update this documentation
* Linting must pass (just run tox)

When sending the pull request, make sure it is rebased against master.
