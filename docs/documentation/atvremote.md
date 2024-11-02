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

# Set up a device with wizard

The atvremote command exposes more or less all functionality of pyatv, thus making it great
for exploring what pyatv can do. Version 0.14.0 introduced a *wizard* to simplify setting up
a new device (in case you don't care about the details). It will scan for devices and guide
you through all the required steps and save credentials to a file, so you don't have to care
about them ever again.

To get going, just run `atvremote wizard`:

```raw
$ atvremote wizard
Looking for devices...
Found the following devices:
    Name                      Model                    Address
--  ------------------------  -----------------------  -----------
 1  Receiver+                 airupnp                  10.0.10.200
 2  Receiver                  RX-V773                  10.0.10.82
 3  Pierre's AirPort Express  AirPort Express (gen 2)  10.0.10.168
 4  FakeATV                   Unknown                  10.0.10.254
 5  Vardagsrum                Apple TV 4K              10.0.10.81
 6  Apple TV                  Apple TV 3               10.0.10.83
Enter index of device to set up (q to quit): 4
Starting to set up FakeATV
Starting to pair Protocol.MRP
Enter PIN on screen: 1111
Successfully paired Protocol.MRP, moving on...
Pairing finished, trying to connect and get some metadata...
Currently playing:
  Media type: Music
Device state: Playing
       Title: Never Gonna Give You Up
      Artist: Rick Astley
    Position: 1/213s (0.0%)
      Repeat: Off
     Shuffle: Off
Device is now set up!
```

Here the device named `FakeATV` with IP address 10.0.10.254 is set up. From now on you
can just run `atvremote -s 10.0.10.254 <command>` or `atvremote -n FakeATV <command>` to
interact with it. Skip down to [Working with commands](#working-with-commands) to see
what you can do.

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

*Unless you know exactly what you are doing, just ignore this section.*

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

For testing purposes, it's possible to specify custom MDNS properties using
`--service-properties`. This might be useful to tinker with certain flags that
alter protocol behavior. The format looks like this:

    Xvar1=value1Xvar2=value2

Where `X` is any character not present in a variable name or value. A typical example
might use `:` or `,` like this:

    :name=test:flags=123

An example call to `atvremote` might look like this:

```shell
$ atvremote --id "aa:bb:cc:dd:ee:ff" --address 10.0.10.253 --port 7000 --manual --protocol raop --service-properties :features=0x4A7FCA00,0xBC354BD0 --debug stream_file=never_gonna_give_you_up.mp3
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

What protocols a device supports can be seen with `scan`. Generally you should pair all protocols
the device supports (beware of protocols marked with *Disabled*: ignore those). Just repeat the
process multiple times, just changing the protocol (`airplay`, `companion`, `dmap`, `mrp` or
`raop`).

*Note: atvremote will automatically store credentials after paring, meaning you do not have to
manually specify them as described in the sections below anymore. See
[Storage and Settings](#storage-and-settings) for more details.*
## Credentials

Once you have paired and received credentials, you may provide said credentials to `atvremote`
via the `--xxx-credentials` flags. Replace `xxx` with a protocol, e.g. `mrp`, `dmap` or `airplay`.  You
may specify multiple credentials:

```shell
$ atvremote -n Kitchen --mrp-credentials abcd --airplay-credentials 1234 playing
```

Manually specifying credentials is no longer needed as `atvrmote` stores credentials persistently
in a file.

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

# Storage and Settings

By default, `atvremote` uses file based storage ({% include api i="storage/file_storage.FileStorage" %})
and saves settings and credentials automatically to `$HOME/.pyatv.conf`. This means that you don't have
to manually provide things like credentials and passwords once they have been saved to storage.

Credentials are saved to the storage automatically after pairing a protocol, i.e. you only need to pair
a protocol once and never care about credentials for that protocol again. Passwords are saved to storage
as well when using one of the `--xxx-password` arguments, thus only needs to be issued once.

Both credentials and passwords will be displayed when performing a scan:

```raw
$ atvremote scan
       Name: Pierre's AirPort Express
   Model/SW: AirPort Express (gen 2), AirPortOS 7.8.1
    Address: 10.0.0.5
        MAC: XX:XX:XX:XX:XX:XX
 Deep Sleep: False
Identifiers:
 - XX:XX:XX:XX:XX:XX
 - XXXXXXXXXXXX
Services:
 - Protocol: AirPlay, Port: 7000, Credentials: creds_airplay, Requires Password: False, Password: airplay_password, Pairing: NotNeeded
 - Protocol: RAOP, Port: 7000, Credentials: creds_raop, Requires Password: False, Password: raop_password, Pairing: NotNeeded
```

You may also look at the settings for a specific device using `print_settings`:

```
$ atvremote -s 10.0.0.5 print_settings
info.name = pyatv (str)
info.mac = 02:70:79:61:74:76 (str)
info.model = iPhone10,6 (str)
info.device_id = FF:70:79:61:74:76 (str)
info.os_name = iPhone OS (str)
info.os_build = 18G82 (str)
info.os_version = 14.7.1 (str)
protocols.airplay.identifier = 58:D3:49:34:A4:B4 (str, NoneType)
protocols.airplay.credentials = None (str, NoneType)
protocols.airplay.password = None (str, NoneType)
protocols.companion.identifier = None (str, NoneType)
protocols.companion.credentials = None (str, NoneType)
protocols.dmap.identifier = None (str, NoneType)
protocols.dmap.credentials = None (str, NoneType)
protocols.mrp.identifier = None (str, NoneType)
protocols.mrp.credentials = None (str, NoneType)
protocols.raop.identifier = 58D34934A4B4 (str, NoneType)
protocols.raop.credentials = None (str, NoneType)
protocols.raop.password = None (str, NoneType)
```

Please note that output may vary depending on the version of pyatv you are using.
The output is agnostic to the underlying storage, i.e. the format will look the
same no matter what storage is used. The following sections describes how to
work with settings in more detail.

## Configuring Storage Module

If you want to change location of your storage, use `--storage-filename` and specify another file.
It is also possible to disable file based storage altogether with `--storage none` (corresponding
to how `atvremote` worked before storage support was added).

At some point pyatv will likely support using custom storage modules as well,
but that is currently not supported.

## Importing Existing Settings

In case you want to "import" credentials you already have, just run `atvremote` with those
credentials and they will be saved to storage automatically. For example, running:

```raw
$ atvrmote -s <ip> --airplay-credentials xxx playing
```

Would save AirPlay credentials. The same thing can be done with passwords as well:

```raw
$ atvrmote -s <ip> --raop-password foobar playing
```

Would save RAOP password to storage. If you want to unset/remote credentials or password, just
pass an empty string:

```raw
$ atvrmote -s <ip> --raop-password "" playing
```

## Changing Individual Settings

To save individual settings, there is a command named `change_setting`. It
accepts a "path" to the setting in the same format as printed by `print_setting`.
Assume you want to change the OS build, look at the output for that setting:

```raw
info.os_build = 18G82 (str)
```

The "path" to this setting is *info.os_build* and it accepts a string (`str`)
as value type. To change this setting, run:

```raw
$ atvremote -s 10.0.10.84 change_setting=info.os_build,19G82
```

If a setting lists `NoneType` as supported type, you can unset the value
like this:

```raw
$ atvremote -s 10.0.10.84 unset_setting=protocols.raop.password
```

As `atvremote` tries to interpolate the correct data type of input (e.g. it
will try to interpret "1" as an integer), you might end up with issues if a
setting expects a number as a string. One example is this:

```raw
protocols.raop.protocol_version = auto (AirPlayVersion)
```

`AirPlayVersion` can be either auto, 1 or 2. Trying to change to 1 yields
an error:

```raw
$ atvremote -s 10.0.10.84 change_setting=protocols.raop.protocol_version,1
Traceback (most recent call last):
...
protocol_version
  Input should be a valid string [type=string_type, input_value=1, input_type=int]
    For further information visit https://errors.pydantic.dev/2.1/v/string_type
```

It expects a string but `atvremote` automatically converts 1 to an integer. To
circumvent this, you can force an argument to be treated as a string like this:

```raw
$ atvremote -s 10.0.10.81 'change_setting=protocols.raop.protocol_version,"1"'
```



## Removing Settings

To remove all settings for a device (reverting to defaults), run:

```raw
$ atvrmote -s <ip> remove_settings
```

Please beware that you lose everything saved for that device, including
credentials and passwords!

# Working with commands
<a name="working-with-commands"></a>

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

Artwork with a specific size (width, height) and filename:

```shell
$ atvremote --id 00:11:22:33:44:54 artwork_save=300,-1,foobar.jpg
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

Show app currently playing something:

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

## Output devices

Show current output devices:

```shell
$ atvremote --id 00:11:22:33:44:54 --airplay-credentials `cat airplay_credentials` output_devices
Device: Living room (AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE), Device: Bedroom (FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ)
```

Only the AirPlay leader device returns the list of output devices, other
connected AirPlay devices will return an empty list.

Add output devices:

```shell
$ atvremote --id 00:11:22:33:44:54 --airplay-credentials `cat airplay_credentials` add_output_devices=FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ,KK:LL:MM:NN:OO:PP
```

Remove output devices:

```shell
$ atvremote --id 00:11:22:33:44:54 --airplay-credentials `cat airplay_credentials` remove_output_devices=AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE,FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ
```

Set output devices:

```shell
$ atvremote --id 00:11:22:33:44:54 --airplay-credentials `cat airplay_credentials` 
set_output_devices=AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE,FFFFFFFF-GGGG-HHHH-IIII-JJJJJJJJJJJJ,KK:LL:MM:NN:OO:PP
```

To discover device IDs to use with these commands, add the devices through the
iOS UI, then use the `output_devices` command.


# Logging and debugging

You can enable additional debugging information by specifying
either `--verbose` or `--debug`. See
[Logging](../../development/logging#bundled-scripts) for additional log options.
