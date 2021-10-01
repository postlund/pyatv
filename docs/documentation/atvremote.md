---
layout: template
title: atvremote
permalink: /documentation/atvremote/
link_group: documentation
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}


# atvremote

To more easily test pyatv, the atvremote application can be used. It is bundled with
pyatv and supports all the functionality implemented by the library. So it is also a
good place to go to for inspiration when implementing your own application.

# Discovering devices

To find devices, use the `scan` command:

```raw
$ atvremote scan
========================================
        Name: Living Room
    Model/SW: 4K tvOS 13.3.1 build 17K795
    Address: 10.0.0.10
        MAC: AA:BB:CC:DD:EE:FF
    Deep Sleep: False
Identifiers:
    - 01234567-89AB-CDEF-0123-4567890ABCDE
    - 00:11:22:33:44:55
Services:
    - Protocol: Companion, Port: 49153, Credentials: None
    - Protocol: MRP, Port: 49152, Credentials: None
    - Protocol: AirPlay, Port: 7000, Credentials: None

        Name: Kitchen
    Model/SW: 3 ATV SW
    Address: 10.0.0.11
    MAC: AA:AA:AA:AA:AA:AA
Identifiers:
    - ABCDEFABCDEFABCD
    - AA:BB:CC:DD:EE:FF
Services:
    - Protocol: AirPlay, Port: 7000, Credentials: None
    - Protocol: DMAP, Port: 3689, Credentials: 00000000-1111-2222-3333-444455556666
```

In this case two devices were found, one named `Living Room` and another named
`Kitchen`. You can read more about what everything means under [Concepts](concepts.md).

## Discovering specific devices

A normal `scan` uses multicast to discover all devices on the network. It is possible to
scan for specific devices ("unicast") by specifying `--scan-hosts`:

```raw
$ atvremote --scan-hosts 10.0.0.10 scan
========================================
        Name: Living Room
    Model/SW: 4K tvOS 13.3.1 build 17K795
    Address: 10.0.0.10
        MAC: AA:BB:CC:DD:EE:FF
    Deep Sleep: False
Identifiers:
    - 01234567-89AB-CDEF-0123-4567890ABCDE
    - 00:11:22:33:44:55
Services:
    - Protocol: MRP, Port: 49152, Credentials: None
    - Protocol: AirPlay, Port: 7000, Credentials: None
```

This yields the same result, but is much faster as it only has to wait for response from
one device. Downside is of course that it cannot automatically find devices, you must know the
IP-address. Multiple devices can be specified as a comma-separated list:

```shell
$ atvremote --scan-hosts 10.0.0.10,10.0.0.11 scan
```

If you have problems using regular scanning or have configured a static address on your Apple TV,
this is the recommended way of finding your devices. Please do note that you should not manually
specify address, port, etc. when using this method. It is not necessary.

The `--scan-hosts` flag can be used with any other command as well:

```shell
$ atvremote --scan-hosts 10.0.0.10 -n Kitchen <some command>
```

## Discovering specific protocols

By default, pyatv will scan for all protocols supported by a device. It is however possible
to be more specific about which protocols to scan for with `--scan-protocols`:

```raw
$  atvremote --scan-protocols mrp scan
Scan Results
========================================
       Name: Vardagsrum
   Model/SW: Gen4K tvOS 14.x build 18L569
    Address: 10.0.0.10
        MAC: AA:BB:CC:DD:EE:FF
 Deep Sleep: False
Identifiers:
 - 01234567-89AB-CDEF-0123-4567890ABCDE
Services:
 - Protocol: MRP, Port: 49153, Credentials: None
```

Only the specified protocols are scanned for. Multiple protocols can be specified
as a comma-separated list:

```raw
$ atvremote --scan-protocols mrp,raop,companion scan
```

## Specifying a device

In order for `atvremote` to know which device you want to control, you must specify the
`--id` flag (or `-i` for short) together with an identifier. You may choose any of the available
identifiers.

Based on the output in the previous chapter, you may write:

```shell
$ atvremote -i 00:11:22:33:44:54 <some command>
```

But this would also work equally good:

```shell
$ atvremote -i 01234567-89AB-CDEF-0123-4567890ABCDE <some command>
```

It is also possible to use the device name by specifying `-n` instead:

```shell
$ atvremote -n "Living Room" <some command>
```

## Manually specifying a device

It is possible to bypass the automatic scanning that `atvremote` performs
by passing the `--manual` flag. This is convenient if you rely on an external
scanning process or to shorten the turn-around time during development testing.
However, doing so means that you mainly lose all benefits of unique identifiers.
They lose meaning completely. Only use this mode if you know what you are doing
and refrain from using this in conjunction with `--scan-hosts`!

When specifying `--manual` you *must* also specify `--address`, `--port`, `--protocol`
and `--id`. Even though the identifier is not used (or applicable), you must
still specify something. A simple call example looks like this:

```shell
$ atvremote --manual --address 10.0.0.10 --port 49152 --protocol mrp --id test playing
```

# Pairing with a device

In most cases you have to pair with a device and obtain *credentials* in order to communicate
with it. To pair you must specify a device, which protocol to pair and use the `pair` command:

```raw
$ atvremote --id 00:11:22:33:44:55 --protocol mrp pair
Enter PIN on screen: 1234
Pairing seems to have succeeded, yey!
You may now use these credentials: xxxx
```

Which protocols a device supports can be seen with `scan`. But in general you need to pair
either `mrp` (devices running tvOS) or `dmap` (Apple TV 3 and earlier). If you also want to
stream video, you can pair `airplay` as well. The procedure is the same for all of them, just
change the argument provided to `--protocol`.

## Credentials

Once you have paired and received credentials, you must provide said credentials to `atvremote`
via the `--xxx-credentials` flags. Replace `xxx` with either `mrp`, `dmap` or `airplay`.  You
may specify multiple credentials:

```shell
$ atvremote -n Kitchen --mrp-credentials abcd --airplay-credentials 1234 playing
```

In the future, `atvremote` will likely store these automatically for you. But as of right now, you
have to manage the credentials yourself. Follow progress at
{% include issue no="243" %}.

## Password

The `raop` protocol optionally requires a password. You may specify a password using the `raop-password` flag. 

```
atvremote --id 00:11:22:33:44:55 --raop-password mypassword stream_file=mymusicfile.mp3
```

# Push updates

With `atvremote` you can use `push_updates` to display current play status automatically
without having to ask the device for it:

```raw
$ atvremote -n Kitchen push_updates
Press ENTER to stop
    Media type: Unknown
Device state: Paused
--------------------
```

Updates will be displayed when they happen. Just press ENTER to stop.

# Working with commands

List supported commands:

```raw
$ atvremote commands
Remote control commands:
- down - Press key down
- home - Press key home
- home_hold - Hold key home
- left - Press key left
- menu - Press key menu
- next - Press key next
- pause - Press key play
- play - Press key play
- play_pause - Toggle between play and pause
...
```

If you want additional help for a specific command, use help:

```shell
$ atvremote help pair
COMMAND:
>> pair(self)

HELP:
Pair pyatv as a remote control with an Apple TV.
```

Multiple commands can be specified a the same time and there's also a `delay` that sleeps
a certain amount of milliseconds before next command is executed. Here's an example where
`select` is pressed, followed by `left` after waiting a second:

```raw
$ atvremote --id 00:11:22:33:44:54 select delay=1000 left
```
## Play Status

Get what is currently playing with `playing`:

```raw
$ atvremote --id 00:11:22:33:44:54 playing
    Media type: Music
Device state: Playing
    Position: 0/397s (0.0%)
        Repeat: Off
        Shuffle: False
```

Artwork with a specific size (width,height):

```shell
$ atvremote --id 00:11:22:33:44:54 artwork_save=300,-1
```

Using -1 will let the device decide that parameter in order to keep aspect ratio.

## Remote Control

Navigation and playback control:

```shell
$ atvremote --id 00:11:22:33:44:54 left
$ atvremote --id 00:11:22:33:44:54 menu
$ atvremote --id 00:11:22:33:44:54 play
```

Seek in the currently playing media:

```shell
$ atvremote --id 00:11:22:33:44:54 set_position=123
```

## Device Information

Check operating system version:

```raw
$ atvremote --id 00:11:22:33:44:54 version
13.3.1
```

Or all device information (same as seen with `atvremote scan`):

```raw
$ atvremote --id 00:11:22:33:44:54 device_info
Model/SW: 4K tvOS 13.3.1 build 17K795
        MAC: 00:11:22:33:44:55
```

## Supported Features

```raw
$ atvremote -n Vardagsrum -s 10.0.10.81 features
Feature list:
-------------
Up: Available
Down: Available
Left: Available
Right: Available
...

Legend:
-------
Available: Supported by device and usable now
Unavailable: Supported by device but not usable now
Unknown: Supported by the device but availability not known
Unsupported: Not supported by this device (or by pyatv)
```

## Apps

Show active app:

```shell
$ atvremote --id 00:11:22:33:44:54 app
App: Musik (com.apple.TVMusic)
```

List installed apps:

```shell
$ atvremote --id 00:11:22:33:44:54 --companion-credentials `cat companion_credentials` app_list
App: Podcaster (com.apple.podcasts), App: Filmer (com.apple.TVMovies), App: TV (com.apple.TVWatchList), App: Bilder (com.apple.TVPhotos), App: App Store (com.apple.TVAppStore), App: C More (se.cmore.CMore2), App: Arcade (com.apple.Arcade), App: Sök (com.apple.TVSearch), App: Emby (emby.media.emby-tvos), App: TV4 Play (se.tv4.tv4play), App: Datorer (com.apple.TVHomeSharing), App: YouTube (com.google.ios.youtube), App: Test (in.staahl.TvOS), App: SVT Play (se.svtplay.mobil), App: Plex (com.plexapp.plex), App: Viafree (com.MTGx.ViaFree.se), App: Inställningar (com.apple.TVSettings), App: Apple Events (com.apple.appleevents), App: discovery+ (com.kanal5.play), App: Netflix (com.netflix.Netflix), App: Viaplay (se.harbourfront.viasatondemand), App: Musik (com.apple.TVMusic)
```

Launching an app:

```shell
$ atvremote -s 10.0.10.81 --companion-credentials `cat companion_credentials` launch_app=com.netflix.Netflix
```

## Streaming

Play a video via AirPlay:

```shell
$ atvremote --id 00:11:22:33:44:54 play_url=http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4
```

Stream an audio file via AirPlay (RAOP):

```shell
$ atvremote --id 00:11:22:33:44:54 stream_file=sample.mp3
```

Stream audio from another process (`ffmpeg` in this case):

```shell
ffmpeg -i sample.wav -f mp3 - | atvremote -s 10.0.10.194 --debug set_volume=80 stream_file=-
```

## Power management

You can turn your Apple TV on:

    $ atvremote -i 00:11:22:33:44:54 turn_on

Or turn it off:

    $ atvremote -i 00:11:22:33:44:54 turn_off

Or check the current power state:

    $ atvremote -i 00:11:22:33:44:54 power_state

# Logging and debugging

You can enable additional debugging information by specifying
either `--verbose` or `--debug`. See
[Logging](../../development/logging#bundled-scripts) for additional log options.
