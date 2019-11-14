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

### Specifying a device

## Pairing with a device

### Credentials

## Push updates

## Working with commands

Several commands are supported by the library. Easiest is just to use the command
called `commands`, as it will present a list of availble commands:

    $ atvremote --id 40:CB:C0:A8:DE:9A commands
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
     - set_position - Seek in the current playing media - set_repeat - Change repeat mode
     - set_shuffle - Change shuffle mode to on or off
     - stop - Press key stop
     - suspend - Suspend the device
     - top_menu - Go to main menu (long press menu)
     - up - Press key up

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

Playing a video via AirPlay:

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