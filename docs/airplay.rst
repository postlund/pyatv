.. _pyatv-airplay:

AirPlay Support
====================
Currently there is some AirPlay functionality supported in pyatv, but it is
very limited. Only two features are supported:

- Device authentication
- Playing media via URL

Additional features will be added as needed.

Device Authentication
---------------------
In tvOS 10.2, Apple started to enforce a feature called "device authentication".
This requires every device that streams content via AirPlay to enter a PIN code
the first time before playback is started. Once done, the user will never have
to do this again. The actual feature has been available for a while but as
opt-in, so it would have to be explicitly enabled. Now it is enabled by default
and cannot be disabled. Devices not running tvOS (e.g. Apple TV 2nd and 3rd
generation) are not affected, even though device authentication can be enabled
on theses devices as well.

The device authentication process is based on the *Secure Remote Password*
protocol (SRP), with slight modifications. All the reverse engineering required
for this process was made by funtax (GitHub username) and has merly been ported
to python for usage in this library. Please see references at bottom of page
for reference implementation.

Generating credentials
^^^^^^^^^^^^^^^^^^^^^^
When performing device authentication, a device identifier and a private key is
required. Once authenticated, they can be used to authenticate without using a
PIN code. So they must be saved and re-used whenever something is to be played.

In this library, the device identifier and private key is called
*AirPlay credentials* and are concatenated into a string, using : as separator.
An example might look like this:

.. code::

  D9B75D737BE2F0F1:6A26D8EB6F4AE2408757D5CA5FF9C37E96BEBB22C632426C4A02AD4FA895A85B
         ^                       ^
    Identifier              Private key

New (random) credentials can be generated and loaded in the following way:

.. code:: python

    credentials = yield from atv.airplay.generate_credentials()
    yield from atv.airplay.load_credentials(credentials)

It is important to load the newly created credentials as they are not
automatically loaded when being generated. This is also how previously
authenticated credentials are re-used.

.. note::

   There is no builtin support for storing credentials. It is up to the
   application to handle this.

API Reference: :py:meth:`pyatv.interface.AirPlay.generate_credentials`,
:py:meth:`pyatv.interface.AirPlay.load_credentials`

Authenticating credentials
^^^^^^^^^^^^^^^^^^^^^^^^^^
Performing the authentication requires two steps. First, the process must be
initiated with the device so that a PIN code is displayed. Then it can be
completed by providing the PIN code back to the library:

.. code:: python

    yield from atv.airplay.start_authentication()
    pin = ...  # Get PIN from user
    yield from atv.airplay.finish_authentication(pin)

If the authentication process fails, a
:py:class:`pyatv.exceptions.DeviceAuthenticationError` is raised.

API Reference: :py:meth:`pyatv.interface.AirPlay.start_authentication`,
:py:meth:`pyatv.interface.AirPlay.finish_authentication`

Verifying credentials
^^^^^^^^^^^^^^^^^^^^^
To verify if the loaded credentials are authenticated, ``verify_authenticated``
can be used:

.. code:: python

    credentials = ...
    yield from atv.airplay.load_credentials(credentials)
    yield from atv.airplay.verify_authenticated()

If the credentials are not properly authenticated, a
:py:class:`pyatv.exceptions.DeviceAuthenticationError` is raised.

API Reference: :py:meth:`pyatv.interface.AirPlay.verify_authenticated`

Example
^^^^^^^
A complete code example of the authentication might look like this (it's
available under ``examples``):

.. code:: python

    import sys
    import asyncio
    from pyatv import (exceptions, helpers)


    @asyncio.coroutine
    def authenticate_with_device(atv):
        """Perform device authentication and print credentials."""
        credentials = yield from atv.airplay.generate_credentials()
        yield from atv.airplay.load_credentials(credentials)

        try:
            yield from atv.airplay.start_authentication()
            pin = input('PIN Code: ')
            yield from atv.airplay.finish_authentication(pin)
            print('Credentials: {0}'.format(credentials))

        except exceptions.DeviceAuthenticationError:
            print('Failed to authenticate', file=sys.stderr)


    helpers.auto_connect(authenticate_with_device)

Playing media
-------------
Playing a URL is as simple as passing the URL to ``play_url``:

.. code:: python

    url = 'http://...'
    yield from atv.airplay.play_url(url)

If the device requires device authentication, valid credentials must be loaded
using :py:meth:`pyatv.interface.AirPlay.load_credentials` first. Otherwise an
error message will be shown on the screen.

References
----------
https://github.com/funtax/AirPlayAuth
https://nto.github.io/AirPlay.html
