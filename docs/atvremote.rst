.. _pyatv-atvremote:

Reference application: atvremote
================================

To more easily test pyatv, the ``atvremote`` application can be used. It is
bundled with pyatv and supports all the functionality implemented by the library.
So it is also a good place to go to for inspiration when implementing your own
application.

Discovering devices
-------------------
If you want to automatically discover devices on your network, use the scan
command:

.. code:: bash

    $ atvremote scan
    Found Apple TVs:
    - Apple TV at 10.0.10.22 (login id: 00000000-1234-5678-9abc-def012345678)

In case you have multiple devices, they should all show up. The discovery
process is performed for 3 seconds, which might be too short and sometimes
a device might not show up. Either just try again or raise the discover
time with the -t flag, e.g. ``atvremote -t 10 scan``.

More details about the discovery process can be found
:ref:`here<pyatv-finding-devices>`.

Pairing with a device
---------------------
To pair with a device, use the ``pair`` command. By default, it will wait
one minute for the pairing process to complete. The remote control will be
announced with name *pyatv* and PIN code to be used is 1234:

.. code:: bash

    $ atvremote pair
    Use pin 1234 to pair with "pyatv" (waiting for 60s)
    After successful pairing, use login id 0x0000000000000001
    Note: If remote does not show up, reboot you Apple TV

You can override all of the settings using ``--remote-name``, ``--pin`` and
``--pairing-timeout``.

.. note::

    It is hardcoded into pyatv so that pairing guid ``0x0000000000000001``
    must always be used. So, if you have paired your device, just use that
    as login id. It is important that you add ``0x`` in front of the guid!

Specifying a device
-------------------
You have two choices:

* Use ``-a`` that will perform the auto discover process and pick the first
  discovered device
* Run ``scan`` yourself and manually specify IP-address and login id for device

Using the first option is easiest but also the slowest (you have to wait
three seconds every time) and also works poorly with multiple devices.
You can try it out like this:

.. code:: bash

    $ atvremote -a <command>

To manually specify IP-address and login id, just do like this:

.. code:: bash

    $ atvremote --adress <IP> --login_id <LOGIN ID>

Using these methods are mutually exclusive, so you may only pick one.

Working with commands
---------------------
Several commands are supported by the library (and thus the device). Easiest
is just to use the command called ``commands``, as it will present a list of
availble commands:

.. code:: bash

    $ atvremote -a commands
    Remote control commands:
     - play - Press key play
     - down - Press key down
     - left - Press key left
     - right - Press key right
     - previous - Press key previous
     - topmenu - Go to top menu (long press menu)
     - set_position - Seeks in the current playing media
     - menu - Press key menu
     - up - Press key up
     - next - Press key next
     - pause - Press key play
     - select - Press key select

    Metadata commands:
     - artwork - Returns artwork for what is currently playing (or None)
     - playing - Returns what is currently playing

    Playing commands commands:
     - position - Current position in the playing media (seconds)
     - album - Album of the currently playing song
     - play_state - Current play state, e.g. playing or paused
     - artist - Artist of the currently playing song
     - media_type - What type of media is currently playing, e.g. video, music
     - total_time - Total play time in seconds
     - title - Title of the current media, e.g. movie or song name

You can for instance get what is currently playing with ``playing``:

.. code:: bash

    atvremote -a playing
    album: None
    artist: None
    media_type: 1
    play_state: 1
    position: 0
    title: None
    total_time: 0

Or seek in the currently playing media:

.. code:: bash

    atvremote -a set_position=123

Logging and debugging
---------------------
You can enable additional debugging information by specifying either
``--verbose`` or ``--debug``. There are also some additional developer commands
that might be useful, if you also specify ``--developer``. They will
show up if you query all available commands.
