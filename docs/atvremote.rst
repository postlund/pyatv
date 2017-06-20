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

    Note: You must use 'pair' with devices that have home sharing disabled

In case you have multiple devices, they should all show up. The discovery
process is performed for 3 seconds, which might be too short and sometimes
a device might not show up. Either just try again or raise the discover
time with the -t flag, e.g. ``atvremote -t 10 scan``.

More details about the discovery process can be found
:ref:`here<pyatv-finding-devices>`.

Pairing with a device
---------------------
To pair with a device, use the ``pair`` command. The remote control will be
announced with name *pyatv*, PIN code to be used is 1234 and a random pairing
guid is generated:

.. code:: bash

    $ atvremote pair
    Use pin 1234 to pair with "pyatv" (press ENTER to stop)
    Using pairing guid: 0x2F2C71E9D2A087DB
    Note: If remote does not show up, try rebooting your Apple TV
    <Pair with device and press ENTER when done>
    Pairing seems to have succeeded, yey!
    You may now use this login id: 0x2F2C71E9D2A087DB

You can override the settings using ``--remote-name``, ``--pin`` and
``--pairing-guid``. When you are done or if you want to abort, just press
ENTER. If the pairing succeeded (after pressing ENTER), this will be
acknowledged with a message.

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

    $ atvremote --address <IP> --login_id <LOGIN ID>

Using these methods are mutually exclusive, so you may only pick one.

Push updates
------------
It is possible to listen for and print push updates as they happen using the
``push_updates`` command:

.. code:: bash

    $ atvremote -a push_updates
    Press ENTER to stop
    Media type: Music
    Play state: Loading
         Title: Namnlös
        Artist: Okänd artist
         Album: Okänt album
      Position: 0/4294966s (0.0%)
        Repeat: Off
       Shuffle: False
    --------------------
    Media type: Music
    Play state: Loading
    --------------------
    Media type: Music
    Play state: Paused
      Position: 0/397s (0.0%)
    --------------------
    Media type: Music
    Play state: Playing
      Position: 0/397s (0.0%)
    --------------------
    Media type: Music
    Play state: Paused
      Position: 7/397s (1.8%)
    --------------------
    Media type: Music
    Play state: Loading
         Title: Namnlös
        Artist: Okänd artist
         Album: Okänt album
      Position: 0/4294966s (0.0%)
        Repeat: Off
       Shuffle: False
    --------------------
    Media type: Unknown
    Play state: No media
    --------------------

Just press ENTER to stop.

AirPlay Device Authentication
-----------------------------
To play a URL with AirPlay on a device running tvOS 10.2 or later, *device
authentication* must be performed (or if it has been explicitly enabled).
Simply use the ``auth`` command for this:

.. code:: bash

    $ atvremote -a auth
    Enter PIN on screen: 1234  # Pin code displayed on screen
    You may now use these credentials:
    D9B75D737BE2F0F1:6A26D8EB6F4AE2408757D5CA5FF9C37E96BEBB22C632426C4A02AD4FA895A85B

The generated credentials must be used every time something is to be played
(otherwise a PIN will be required again). So make sure to save it somewhere.

To play a URL, then just use ``play_url`` and provide the credentials:

.. code:: bash

    $ atvremote -a --airplay_credentials D9B75D737BE2F0F1:6A26D8EB6F4AE2408757D5CA5FF9C37E96BEBB22C632426C4A02AD4FA895A85B play_url=<some URL here>

Working with commands
---------------------
Several commands are supported by the library (and thus the device). Easiest
is just to use the command called ``commands``, as it will present a list of
availble commands:

.. code:: bash

    $ atvremote -a commands
    Remote control commands:
     - down - Press key down
     - left - Press key left
     - menu - Press key menu
     - next - Press key next
     - pause - Press key play
     - play - Press key play
     - previous - Press key previous
     - right - Press key right
     - select - Press key select
     - set_position - Seek in the current playing media
     - set_repeat - Change repeat mode
     - set_shuffle - Change shuffle mode to on or off
     - stop - Press key stop
     - top_menu - Go to main menu (long press menu)
     - up - Press key up

    Metadata commands:
     - artwork - Return artwork for what is currently playing (or None)
     - artwork_url - Return artwork URL for what is currently playing
     - device_id - Return a unique identifier for current device
     - playing - Return what is currently playing

    Playing commands:
     - album - Album of the currently playing song
     - artist - Artist of the currently playing song
     - hash - Create a unique hash for what is currently playing
     - media_type - Type of media is currently playing, e.g. video, music
     - play_state - Play state, e.g. playing or paused
     - position - Position in the playing media (seconds)
     - repeat - Repeat mode
     - shuffle - If shuffle is enabled or not
     - title - Title of the current media, e.g. movie or song name
     - total_time - Total play time in seconds

    AirPlay commands:
     - finish_authentication - End authentication process with PIN code
     - generate_credentials - Create new credentials for authentication
     - load_credentials - Load existing credentials
     - play_url - Play media from an URL on the device
     - start_authentication - Begin authentication proces (show PIN on screen)
     - verify_authenticated - Check if loaded credentials are verified

    Device commands:
     - artwork_save - Download artwork and save it to artwork.png
     - auth - Perform AirPlay device authentication
     - push_updates - Listen for push updates

    Global commands:
     - commands - Print a list with available commands
     - help - Print help text for a command
     - pair - Pair pyatv as a remote control with an Apple TV
     - scan - Scan for Apple TVs on the network

You can for instance get what is currently playing with ``playing``:

.. code:: bash

    $ atvremote -a playing
    Media type: Music
    Play state: Playing
      Position: 0/397s (0.0%)
        Repeat: Off
       Shuffle: False

Or seek in the currently playing media:

.. code:: bash

    $ atvremote -a set_position=123

If you want additional help for a specific command, use ``help``:

.. code:: bash

    $ atvremote help pair
    COMMAND:
    >> pair(self)

    HELP:
    Pair pyatv as a remote control with an Apple TV.

Logging and debugging
---------------------
You can enable additional debugging information by specifying either
``--verbose`` or ``--debug``.
