---
layout: template
title: Stream
permalink: /development/stream/
link_group: development
---
 Table of Contents
{:.no_toc}
* TOC
{:toc}

# Stream

It is possible to stream audio and video to a device via the stream interface using
AirPlay. The AirPlay suite consists of two protocols:

* AirTunes/RAOP - Used for real time streaming of audio
* "AirPlay - Everything else (video, images and screen mirroring)

Currently there is some AirPlay functionality supported in pyatv, but it is
very limited. These features are currently supported:

- Device authentication ("pairing")
- Playing media via URL
- Streaming of local files

Early support for streaming audio files via RAOP is also supported
(even for non-Apple TV devices). MP3, wav, FLAC and ogg files are
supported. Devices that require a password are only supported for the AirTunes/RAOP protocol, not the AirPlay protocol. 

In the external interface, AirPlay (including RAOP) support is implemented via
the {% include api i="interface.Stream" %} interface.

## Using the streaming API

Devices supporting the AirPlay protocol (e.g. Apple TV) can play files by simply providing
a URL. It will then be streamed directly from the device. Audio can be streamed to other
devices (like AirPlay speakers) that does not support this.

### Play from URL

Playing a URL is as simple as passing the URL to {% include api i="interface.Stream.play_url" %}:

```python
url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
await atv.stream.play_url(url)
```

If the device requires device authentication, credentials must be present for
the AirPlay service. Otherwise an error message will be shown on the screen.

To play a local file, just pass a local file to {% include api i="interface.Stream.play_url" %}
instead:

```python
url = "/home/user/BigBuckBunny.mp4"
await atv.stream.play_url(url)
```

When doing this, pyatv will internally start web server on a random port, serving this
file only and start streaming from there. When streaming is done, the web server is shut
down.

The Apple TV will not provide any feedback if anything is not working. If you have
problems, start by testing the example file above (`BigBuckBunny.mp4`) as that is
known to work. Also make sure that you don't stream from an HTTPS server with a bad
or self-signed certificate: that will not work.

### Stream a file

To stream a file, use {% include api i="interface.Stream.stream_file" %}:

```python
stream = ...
await stream.stream_file("sample.mp3")
```

Files in MP3, wav, FLAC and ogg format are supported and will be automatically converted
to a format the receiving device supports. Metadata is also extracted from files
of these types and sent to the receiver.

It is also possible to stream directly from a buffer. In this example, a file is
read into a buffer and streamed:

```python
import io

with io.open("myfile.mp3", "rb") as source_file:
    await stream.stream_file(source_file)
```

Streaming directly from `stdin` also works, e.g. when piping output from another
process:

```python
await stream.stream_file(sys.stdin.buffer)
```

As `stdin` is a text stream, the underlying binary buffer must be retrieved and used.

When streaming from a buffer, it's important to know that some audio formats are
not suitable for that. MP3 works fine, WAV and OGG does not. The reason is that
seeking is done in the stream and `stdin` does for instance not support that. If
the buffer supports seeking, then all formats will work fine, otherwise stick with
MP3. For the same reason, metadata will not work if seeking is not supported as
that is extracted prior to playing the file, so seeking is needed to return to
the beginning of file again before playback.

Note that there's (roughly) a two second delay until audio starts to play. This
is part of the buffering mechanism and not much pyatv can do anything about.

#### File Compatibility

It is possible to verify if a file is supported programmatically using
{% include api i="helpers.is_streamable" %}:

```python
from pyatv.helpers import is_streamable

if await is_streamable("myfile.mp3"):
    await atv.stream_file("myfile.mp3")
else:
    print("File is not supported")
```

There are a few caveats worth knowing:

* No exception is ever raised, even when file is not found or lack of permissions
* Only valid for {% include api i="interface.Stream.stream_file" %} (*not*
  {% include api i="interface.Stream.play_url" %})
* Only a basic check is made, the file might be broken and not still not playable

## Password

If you stream audio using the RAOP protocol and the device requires a password, you can set the password like this: 

```python
raop_service = atv_conf.get_service(Protocol.RAOP)
raop_service.password = "test"
atv = await connect(atv_conf, ...)
await atv.stream.stream_file("sample.mp3")
```

## Device Authentication

In tvOS 10.2, Apple started to enforce a feature called "device authentication".
This requires every device that streams content via AirPlay to enter a PIN code
the first time before playback is started. Once done, the user will never have
to do this again. The actual feature has been available for a while but as
opt-in, so it would have to be explicitly enabled. Now it is enabled by default
and cannot be disabled. Devices not running tvOS (e.g. Apple TV 2nd and 3rd
generation) are not affected, even though device authentication can be enabled
on these devices as well.

The device authentication process is based on the *Secure Remote Password*
protocol (SRP), with slight modifications. All the reverse engineering required
for this process was made by funtax (GitHub username) and has merely been ported
to python for usage in this library. Please see references at bottom of page
for reference implementation.

### Device Pairing in pyatv

When performing device authentication, a device identifier and a private key is
required. Once authenticated, they can be used to authenticate without using a
PIN code. So they must be saved and re-used whenever something is to be played.

In this library, the device identifier and private key is called
*AirPlay credentials* and are concatenated into a string, using : as separator.
An example might look like this:

```raw
D9B75D737BE2F0F1:6A26D8EB6F4AE2408757D5CA5FF9C37E96BEBB22C632426C4A02AD4FA895A85B
        ^                       ^
    Identifier              Private key
```

The device authentication is performed via the pairing API, just like with
any other protocol. New random credentials are generated by default, as long
as no existing credentials are provided. So there is nothing special here.
