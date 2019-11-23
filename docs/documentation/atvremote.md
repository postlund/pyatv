---
layout: template
title: atvremote
permalink: /documentation/atvremote/
link_group: documentation
---
# atvremote

To more easily test pyatv, the atvremote application can be used. It is bundled with
pyatv and supports all the functionality implemented by the library. So it is also a
good place to go to for inspiration when implementing your own application.

## Discovering devices

To find devices, use the `scan` command:

    $ atvremote scan
    ========================================
           Name: Living Room
        Address: 10.0.0.10
    Identifiers:
     - 01234567-89AB-CDEF-0123-4567890ABCDE
     - 00:11:22:33:44:55
    Services:
     - Protocol: MRP, Port: 49152, Credentials: None
     - Protocol: AirPlay, Port: 7000, Credentials: None

           Name: Kitchen
        Address: 10.0.0.11
    Identifiers:
     - ABCDEFABCDEFABCD
     - AA:BB:CC:DD:EE:FF
    Services:
     - Protocol: AirPlay, Port: 7000, Credentials: None
     - Protocol: DMAP, Port: 3689, Credentials: 00000000-1111-2222-3333-444455556666

In this case two devices were found, one named `Living Room` and another named
`Kitchen`. You can read more about what everything means under [Concepts](concepts.md).

### Specifying a device

In order for `atvremote` to know which device you want to control, you must specify the
`--id` flag (or `-i` for short) together with an identifier. You may choose any of the available
identifiers.

Based on the output in the previous chapter, you may write:

    $ atvremote -i 00:11:22:33:44:54 <some command>

But this would also work equally good:

    $ atvremote -i 01234567-89AB-CDEF-0123-4567890ABCDE <some command>

It is also possible to use the device name by specifying `-n` instead:

    $ atvremote -n "Living Room" <some command>

## Pairing with a device

In most cases you have to pair with a device and obtain *credentials* in order to communicate
with it. To pair you must specify a device, which protocol to pair and use the `pair` command:

    $ atvremote --id 00:11:22:33:44:55 --protocol mrp pair
    Enter PIN on screen: 1234
    Pairing seems to have succeeded, yey!
    You may now use these credentials: xxxx

Which protocols a device supports can be seen with `scan`. But in general you need to pair
either `mrp` (devices running tvOS) or `dmap` (Apple TV 3 and earlier). If you also want to
stream video, you can pair `airplay` as well. The procedure is the same for all of them, just
change the argument provided to `--protocol`.

### Credentials

Once you have paired and received credentials, you must provide said credentials to `atvremote`
via the `--xxx-credentials` flags. Replace `xxx` with either `mrp`, `dmap` or `airplay`.  You
may specify multiple credentials:

    $ atvremote -n Kitchen --mrp-credentials abcd --airplay-credentials 1234 playing

In the future, `atvremote` will likely store these automatically for you. But as of right now, you
have to manage the credentials yourself. Follow progress at
[#242](https://github.com/postlund/pyatv/issues/243).

## Push updates

With `atvremote` you can use `push_updates` to display current play status automatically
without having to ask the device for it:

    $ atvremote -n Kitchen push_updates
    Press ENTER to stop
    Media type: Unknown
    Play state: Paused
    --------------------

Updates will be displayed when they happen. Just press ENTER to stop.

## Working with commands

Several commands are supported by the library. Easiest is just to use the command
called `commands`, as it will present a list of availble commands:

    $ atvremote --id 40:CB:C0:A8:DE:9A commands
    Remote control commands:
     - down - Press key down
     - home - Press key home
     - home_hold - Hold key home
     - left - Press key left
     - menu - Press key menu
     - next - Press key next
     - pause - Press key play
     - play - Press key play
     - previous - Press key previous
     - right - Press key right
     - select - Press key select
     - set_position - Seek in the current playing media - set_repeat - Change repeat mode
     - set_shuffle - Change shuffle mode to on or off
     - stop - Press key stop
     - suspend - Suspend the device
     - top_menu - Go to main menu (long press menu)
     - up - Press key up
     - volume_down - Press key volume down
     - volume_up - Press key volume up

    Metadata commands:
     - artwork - Return artwork for what is currently playing (or None)
     - device_id - Return a unique identifier for current device
     - playing - Return what is currently playing

    Playing commands:
     - album - Album of the currently playing song
     - artist - Artist of the currently playing song
     - genre - Genre of the currently playing song
     - hash - Create a unique hash for what is currently playing
     - media_type - Type of media is currently playing, e.g. video, music
     - play_state - Play state, e.g. playing or paused
     - position - Position in the playing media (seconds)
     - repeat - Repeat mode
     - shuffle - If shuffle is enabled or not
     - title - Title of the current media, e.g. movie or song name
     - total_time - Total play time in seconds

    AirPlay commands:
     - play_url - Play media from an URL on the device

    Device commands:
     - artwork_save - Download artwork and save it to artwork.png
     - cli - Enter commands in a simple CLI
     - push_updates - Listen for push updates

    Global commands:
     - commands - Print a list with available commands
     - help - Print help text for a command
     - pair - Pair pyatv as a remote control with an Apple TV
     - scan - Scan for Apple TVs on the network

You can for instance get what is currently playing with `playing`:

    $ atvremote --id 40:CB:C0:A8:DE:9A playing
    Media type: Music
    Play state: Playing
      Position: 0/397s (0.0%)
        Repeat: Off
       Shuffle: False

Or seek in the currently playing media:

    $ atvremote --id 40:CB:C0:A8:DE:9A set_position=123

Play a video via AirPlay:

    $ atvremote --id 40:CB:C0:A8:DE:9A play_url=http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4

If you want additional help for a specific command, use help:

    $ atvremote help pair
    COMMAND:
    >> pair(self)

    HELP:
    Pair pyatv as a remote control with an Apple TV.

### Logging and debugging

You can enable additional debugging information by specifying
either `--verbose` or `--debug.`.