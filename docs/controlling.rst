.. _pyatv-controlling:

Controlling a device
====================
Controlling a device is done with the "remote control" API. It can be fetched
via the `remote_control` attribute after connecting to a device, like so:

.. code:: python

    details = ...
    atv = pyatv.connect_to_apple_tv(details, loop)
    rc = atv.remote_control

All commands are asynchronous, so they must be used in a coroutine. For a
complete list of commands, see :py:class:`pyatv.interface.RemoteControl`.

Performing a command
--------------------
To perform a command is just as easy as calling the method corresponding to
the expected action:

.. code:: python

    yield from atv.remote_control.play()
    yield from atv.remote_control.next()

Commands with arguments
-----------------------
Most commands just performs an action and requires no additional arguments.
Seeking in the currently playing media however, is one command that requires
the desired media position:

.. code:: python

    yield from atv.remote_control.set_position(60)  # 1 minute in
