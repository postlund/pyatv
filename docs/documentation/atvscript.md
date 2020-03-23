---
layout: template
title: atvscript
permalink: /documentation/atvscript/
link_group: documentation
---
# atvscript

This script has been created specifically for scripting purposes or for integration
with existing software without having to write any additional code. It supports a
subset of what `atvremote` supports and always produce output in a format that is
easy to parse, e.g. JSON. It is simple to add support for additional formats if needed.

Extending and improving this script will mostly be left to the community. If you want
a new feature, feel free to send a PR!

## General Output Format

Output is always in the form of a dictionary (be it JSON, YAML or something else) with
the following keys pre-defined keys:

| Key | Meaning |
| --- | ------- |
| result | `success` if command was sucessful, else `failure`.
| error | An error occured and this is a well defined string representing the error. Values: `device_not_found`, `unsupported_command`.
| exception | If an unexpected exception ocurred, this key contains the exception message.

`error` and `exception` will only be present if `result` is set to `failure`. Any
additional keys are part of the command response.


## Specifying Device and Credentials

Currently `atvscript` supports device discovery using regular scanning and unicast
scanning, with identifier as filter. The arguments are identical to [atvremote](/documentation/atvremote):

```shell
$ atvscript --id 12345 xyz
$ atvscript -s 10.0.0.2 xyz
```

Credentials are specified via `--dmap-credentials`, `--mrp-credentials` and
`--airplay-credentials`. Protocol can also be specified with `--protocol`.

When using unicast scanning, i.e. specifying IP address via `-s`, it is not needed to
specify `--id` as the script will pick the first available device it finds. This can
only be the requested device.

## Command Reference

This section documents the supported commands.

### Scanning

It is possible to scan for devices with the `scan` command:

```shell
$ atvscript scan
{"result": "success", "devices": [{"name": "Vardagsrum", "address": "10.0.10.81", "identifier": "xxx", "services": [{"protocol": "mrp", "port": 49152}, {"protocol": "airplay", "port": 7000}]}, {"name": "Apple\u00a0TV", "address": "10.0.10.123", "identifier": "xxx", "services": [{"protocol": "airplay", "port": 7000}, {"protocol": "dmap", "port": 3689}]}, {"name": "Proxy", "address": "10.0.10.254", "identifier": "xxx", "services": [{"protocol": "mrp", "port": 47531}]}]}
```

Scanning also respects the `--scan-hosts` (`-s`) flag, which is useful sometimes if scanning
is flaky:

```shell
$ atvscript -s 10.0.10.81 scan
{"result": "success", "devices": [{"name": "Vardagsrum", "address": "10.0.10.81", "identifier": "xxx", "services": [{"protocol": "mrp", "port": 49152}, {"protocol": "airplay", "port": 7000}]}]}
```

### What is Playing

To get what is playing:

```shell
$ atvscript -s 10.0.10.81 playing
{"result": "success", "hash": "azyFEzFpSNOSGq9ZvcaX4A\u2206DcpumkUoRty+R098MQeIKA", "media_type": "music", "device_state": "paused", "title": "Ordinary World (Live)", "artist": "Duran Duran", "album": "From Mediterranea With Love - EP", "genre": "Rock", "total_time": 395, "position": 1, "shuffle": "off", "repeat": "off", "app": "Musik", "app_id": "com.apple.TVMusic"}
```

Some of the fields, like `media_type` and `device_state` uses the names from their corresponding enum, but in lower case. Check out {% include api i="const.DeviceState" %} for instance to find valid values for `device_state`.

### Remote Control

All buttons in {% include api i="interface.RemoteControl" %} are supported by `atvscript`
except for the ones beginning with `set_`:

```shell
$ atvscript -s 10.0.10.81 menu
{"result": "success", "command": "menu"}
```

### Push and Power Updates

Push and power updates are printed to the terminal as they happen:

```shell
$ atvscript -s 10.0.10.81 push_updates
{"result": "success", "power_state": "off"}
{"result": "success", "hash": "azyFEzFpSNOSGq9ZvcaX4A\u2206DcpumkUoRty+R098MQeIKA", "media_type": "music", "device_state": "paused", "title": "Ordinary World (Live)", "artist": "Duran Duran", "album": "From Mediterranea With Love - EP", "genre": "Rock", "total_time": 395, "position": 1, "shuffle": "off", "repeat": "off", "app": "Musik", "app_id": "com.apple.TVMusic"}
{"result": "success", "power_state": "on"}
{"result": "success", "power_state": "off"}

{"result": "success", "push_updates": "finished"}
```

Current power state is always printed as the first update.

When pressing ENTER, the script will exit (as seen on the last line).
