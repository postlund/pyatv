---
layout: template
title: Tools
permalink: /internals/tools
link_group: internals
---
# :hammer: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Tools

A few tools are shipped with pyatv that are only used internally or serving as help during
development. This page gives a brief introduction to them.

# chickn

Historically pyatv has always used [tox](https://tox.wiki/) as an automation tool to run tests, linters and
so on. It is a great piece of software but has proven to be a bit slow and complex for the use case of
pyatv. From this, a tool named `chickn` emerged (yes, [Not invented here](https://en.wikipedia.org/wiki/Not_invented_here)).
This was seen as an opportunity to learn more about simple command automation and has no goal whatsoever
to compete with `tox`. At this point `chickn` is only distributed with pyatv, but will hopefully move to
a separate project at some point.

## The idea behind chickn

The idea behind `chickn` is very simple: allow shell commands to be run in sequence and parallel according
to a specification. The specification in this case is a `chickn.yml` file. Commands to be run are added as
steps inside a stage, which forms a pipeline. Stages are run sequentially and steps within a stage are run
in parallel.

For the sake of simplicity, only one pipeline is supported per file. There is no concept of tool versions
in `chickn` either, like which python version to use. It is up to the runner to make sure the expected
version is available, which is the normal case when running in a container (the way `chickn` is intended
to run).

### Pipeline, stages and steps

Here's a simple example:

```yaml
pipeline:
  stage1:
    - name: foobar
      run: ls /
  stage2:
    - name: hello
      run: echo helloe
    - name: world
      run: echo world
```

This pipeline consists of two stages. First, all steps in `stage1` are run in parallel (only "foobar" in this case).
Once all steps have finished, the next stage is started and all steps within `stage2` are also run in
parallel. Each step needs a unique name, which can be used to run individual steps from the command line.

### Variables

It is possible to define variables as inputs to a command, which can be altered from the command line. Here
is a simple example of using a variable

```yaml
variables:
  args: -k foobar

pipeline:
  test:
    - name: pytest
      run: pytest {args}
```

This would run the command `pytest -k foobar`, but the arguments can be easily be changed afterwards. Variables
cannot depend on other variables (they will not be resolved).

It is possible to specify variables as lists:

```yaml
variables:
  args:
    - -k
    - foobar

pipeline:
  test:
    - name: pytest
      run: pytest {args}
```

Internally, `chickn` will join all elements of the list with a space, i.e. `args=-k foobar` before
inserting the value into a command.

#### Special variables

These are "special" variables that are automatically set by `chickn`:

| Variable | Value |
| -------- | ----- |
| python_executable | Absolute path to python binary that runs `chickn`, e.g. */workspace/pyatv/bin/python*. |

### Requirements

There is builtin support for installing python packages with pip (this is the only python specific feature
of `chickn`) like this:

```yaml
# chickn.yml
dependencies:
  files:
    - requirements.txt

pipeline:
  pre:
   - name: clean
     run: coverage erase

# requirements.txt
coverage==6.0.2
```

It is not possible to specify individual packages, only requirement files containing packages. Installed
packages will be compared with expected versions and re-installed when needed. This speeds up installation
dramatically, but is also considered "optimistic" (if a package is installed but broken, that will not be
discovered). It's a tradeoff for speed.

*It is assumed that package versions are pinned to a specific version!*

### Tags

Tags can be added to a step, making it possible to enable it when needed on the command line. A step
marked with at least one tag will never run unless one of its tags are provided on the command line!
This can be useful for steps that are not generally run during development, like packaging, but needed
during delivery or in CI.

```yaml
pipeline:
  stages:
    - name: hello
      run: echo helloe
      tags: [test, dummy]
    - name: world
      run: echo world
```

## Using chickn

Currently, `chickn` lives in `scripts/chickn.py` and requires pyyaml to run (as it uses YAML as
configuration format). It must also run in a virtual environment (check can be disabled). To get
going, this is what you need to do:

```shell
$ python -m venv venv
$ source venv/bin/activate  # venv/scripts/activate.bat on Windows
$ pip install pyyaml
$ ./scripts/chickn.py
```

This should run `chickn` and give you output similar to this:

```raw
$ ./scripts/chickn.py
2021-10-24 10:36:01 [INFO] Installing dependencies
2021-10-24 10:36:02 [INFO] All packages are up-to-date
2021-10-24 10:36:02 [INFO] Step install_deps finished in 0.52s
2021-10-24 10:36:02 [INFO] Running pre with 1 steps
2021-10-24 10:36:02 [INFO] Running step clean
2021-10-24 10:36:02 [INFO] Step clean finished in 0.09s
2021-10-24 10:36:02 [INFO] Running validate with 10 steps
2021-10-24 10:36:02 [INFO] Running step pylint
2021-10-24 10:36:02 [INFO] Running step protobuf
2021-10-24 10:36:02 [INFO] Running step flake8
2021-10-24 10:36:02 [INFO] Running step black
2021-10-24 10:36:02 [INFO] Running step pydocstyle
2021-10-24 10:36:02 [INFO] Running step isort
2021-10-24 10:36:02 [INFO] Running step cs_docs
2021-10-24 10:36:02 [INFO] Running step cs_code
2021-10-24 10:36:02 [INFO] Running step typing
2021-10-24 10:36:02 [INFO] Running step pytest
2021-10-24 10:36:03 [INFO] Step protobuf finished in 0.66s
2021-10-24 10:36:03 [INFO] Step cs_docs finished in 0.78s
2021-10-24 10:36:03 [INFO] Step typing finished in 1.00s
2021-10-24 10:36:03 [INFO] Step black finished in 1.10s
2021-10-24 10:36:03 [INFO] Step cs_code finished in 1.39s
2021-10-24 10:36:05 [INFO] Step isort finished in 2.55s
2021-10-24 10:36:10 [INFO] Step flake8 finished in 7.97s
2021-10-24 10:36:18 [INFO] Step pydocstyle finished in 15.86s
2021-10-24 10:36:35 [INFO] Step pylint finished in 33.01s
2021-10-24 10:36:36 [INFO] Step pytest finished in 33.91s
2021-10-24 10:36:36 [INFO] Running post with 1 steps
2021-10-24 10:36:36 [INFO] Running step report
2021-10-24 10:36:41 [INFO] Step report finished in 5.01s
2021-10-24 10:36:41 [INFO] Running package with 0 steps
2021-10-24 10:36:41 [INFO] Finished in 39.64!
```

There is very little error handling in `chickn`, so things will break whenever something
is a little bit off. Improvements will be made over time,

### Running individual steps

To run one or more steps, pass their names as arguments:

```raw
$ ./scripts/chickn.py -- protobuf isort
2021-10-24 10:38:09 [INFO] Installing dependencies
2021-10-24 10:38:09 [INFO] All packages are up-to-date
2021-10-24 10:38:09 [INFO] Step install_deps finished in 0.47s
2021-10-24 10:38:09 [INFO] Running pre with 0 steps
2021-10-24 10:38:09 [INFO] Running validate with 2 steps
2021-10-24 10:38:09 [INFO] Running step protobuf
2021-10-24 10:38:09 [INFO] Running step isort
2021-10-24 10:38:09 [INFO] Step protobuf finished in 0.19s
2021-10-24 10:38:10 [INFO] Step isort finished in 0.65s
2021-10-24 10:38:10 [INFO] Running post with 0 steps
2021-10-24 10:38:10 [INFO] Running package with 0 steps
2021-10-24 10:38:10 [INFO] Finished in 1.13!
```

Make it a custom to use `--` as you might run into problems when using tags or variables
otherwise.

### Overriding variables

One or more variables can be overridden like this:

```raw
$ ./scripts/chickn.py -v myvar=123 -v another_var=456 -- protobuf isort
```

### Failing steps

If a step fails, all currently running steps will be cancelled while printing out stderr and
stdout of the failing step:

```raw
$ ./scripts/chickn.py -t fixup
2021-10-24 11:23:12 [INFO] Installing dependencies
2021-10-24 11:23:13 [INFO] All packages are up-to-date
2021-10-24 11:23:13 [INFO] Step install_deps finished in 1.37s
2021-10-24 11:23:13 [INFO] Running pre with 2 steps
2021-10-24 11:23:13 [INFO] Running step clean
2021-10-24 11:23:13 [INFO] Running step fixup
2021-10-24 11:23:13 [INFO] Step clean finished in 0.28s
2021-10-24 11:23:17 [INFO] Step fixup finished in 3.96s
2021-10-24 11:23:17 [INFO] Running validate with 10 steps
2021-10-24 11:23:17 [INFO] Running step pylint
2021-10-24 11:23:17 [INFO] Running step protobuf
2021-10-24 11:23:17 [INFO] Running step flake8
2021-10-24 11:23:17 [INFO] Running step black
2021-10-24 11:23:17 [INFO] Running step pydocstyle
2021-10-24 11:23:17 [INFO] Running step isort
2021-10-24 11:23:17 [INFO] Running step cs_docs
2021-10-24 11:23:17 [INFO] Running step cs_code
2021-10-24 11:23:17 [INFO] Running step typing
2021-10-24 11:23:17 [INFO] Running step pytest
2021-10-24 11:23:18 [INFO] Step protobuf finished in 0.88s
2021-10-24 11:23:18 [INFO] Step cs_docs finished in 1.21s
2021-10-24 11:23:18 [INFO] Step black finished in 1.41s
2021-10-24 11:23:19 [INFO] Step cs_code finished in 1.88s
2021-10-24 11:23:20 [INFO] Step isort finished in 3.43s
2021-10-24 11:23:21 [INFO] Step typing finished in 4.20s
2021-10-24 11:23:27 [ERROR] At least one task failed
2021-10-24 11:23:27 [ERROR] Task 'flake8' failed (InternalError): Command failed: flake8 --exclude=pyatv/protocols/mrp/protobuf pyatv scripts examples
[STDOUT]
pyatv/scripts/atvremote.py:355:5: F841 local variable 'test' is assigned to but never used


[STDERR]
None
2021-10-24 11:23:27 [ERROR] Tasks failed: flake8
```

### Specifying tags

One or more tags can be set like this:

```raw
$ ./scripts/chickn.py -t tag1 -t tag2 -- all
```

### Some other things

A few other useful things:

* Do not install any packages: `--no-install` (or `-n`)
* Force re-install of packages even if versions match: `--force-pip` (or `-f`)
* Allow running without venv: `--no-venv`
* List all avavilable steps: `--list` (or `-l`)

# Protobuf

This section describes how to work with [Google Protobuf](https://developers.google.com/protocol-buffers/) in pyatv. Protobuf is used by the `MRP` protocol only.

## Definitions

All Protobuf definitions (`.proto` files) are located in `pyatv/mrp/protobuf`. Currently the generated files, including mypy hints (`.pyi`files) are checked in to the repository. Preferably only the `.proto` files should be checked in and in the future this might be the case.

### Wrapper Code

To simplify working with Protobuf messages in code, an auto-generated wrapper is used. This wrapper is generated by `scripts/protobuf.py` and provides some convenience:

* Message constants are available at top level (`CLIENT_UPDATES_CONFIG_MESSAGE` vs `ProtocolMessage.CLIENT_UPDATES_CONFIG_MESSAGE`)
* Messages are more easily available (`SetArtworkMessage` vs `SetArtworkMessage_pb2.SetArtworkMessage`)
* Calling `inner()` will return the encapsulated message from a `ProtocolMessage`

The file is checked into the repository and located here:
{% include code file="mrp/protobuf/__init__.py" %}. See [Making Changes](#making-changes)
on how to generate this file.

You shall *not* modify this file manually. Instead modify the `.proto` files and re-generate
the wrapper code. If something is missing or wrong in the wrapper code, make changes
to `protobuf.py` instead.

### Making Changes

If you add new `.proto` files or modify existing files, you need to re-generate the message files. This is done with `scripts/protobuf.py`:

```shell
$ ./scripts/protobuf.py --download generate
Downloading https://github.com/protocolbuffers/protobuf/...
Extracting bin/protoc
Writing mypy to pyatv/mrp/protobuf/PlaybackQueueCapabilities_pb2.pyi
Writing mypy to pyatv/mrp/protobuf/DeviceInfoMessage_pb2.pyi
...
```
See [Protobuf Compiler](#protobuf-compiler) for more details.

### Verifying Changes

It is possible to verify if current messages are up-to-date using `verify`:

```shell
$ ./scripts/protobuf.py --download verify
Not downloading protoc (already exists)
Generated code is up-to-date!
```

Running `./scripts/chickn.py protobuf` will ensure that this file is up-to-date. It is always run when checking in code.

See [Protobuf Compiler](#the-protobuf-compiler) for more details.

*NB: This only verifies that the wrapper code is up-to-date at the moment.*

### Protobuf Compiler

A specific version of the protobuf compiler is used to generate the message to make sure they are always generated in the same way (version is hardcoded into `protobuf.by` and may be bumped when needed).

The flag `--download` will download and extract `protoc` into the `bin` directory. This works for Linux (x86_64), macOS and Windows (x64). If the file is already downloaded, `--download` does nothing.

`protobuf.py` will verify that the downloaded version matches the version hardcoded into the script before generating messages. If there is a mismatch, just add `--force` to make the script re-download the compiler again.


# Fake Device

A fake device is used in the functional tests to verify that pyatv works as expected. It is however convenient to have a fake device that you can interact with using `atvremote`. The script `scripts/fake_device.py` is supposed to fill this gap until proper support is built into pyatv (see [#334](https://github.com/postlund/pyatv/issues/334) and [#518](https://github.com/postlund/pyatv/issues/518)).

*Beware that command line flags and options might change at any time due to new features. This script is only meant as development aid.*

## Features

This is the current feature set:

* All protocols are supported - amount of functionality varies
* Protocols are found when scanning, e.g. supports Zeroconf
* Device reports idle state (nothing playing) by default
* Commands sent to it are mostly just logged to console
* A "demo" mode is included, which cycles between example video, example music and nothing playing every three seconds

No attempts have been made to integrate this with the real Remote app in iOS, which means that it probably doesn't work. At least basic support for this would be nice.

**Feel free to improve this script and the protocols implemented by fake device!**

## Example Usage

By default, the device will broadcast `127.0.0.1` as IP address in Zeroconf, so it is only usable on localhost. You can change this with `--local-ip`. It is also possible to enable debug logs with `--debug`. No protocol is selected by default, so you need to specify at least one for the script to run (but you may specify as many as you like). Valid flags are `--mrp`, `--mrp` and `--airplay`.

### Single Protocol

Start an `MRP` fake device:

```shell
$ ./scripts/fake_device.py --mrp
Press ENTER to quit
```

Run `atvremote` from another terminal:

```shell
$ atvremote scan
Scan Results
========================================
       Name: FakeATV
   Model/SW: Unknown Model tvOS 13.x build 17K499
    Address: 127.0.0.1
        MAC: 40:CB:C0:12:34:56
Identifiers:
 - 6D797FD3-3538-427E-A47B-A32FC6CF3A69
Services:
 - Protocol: MRP, Port: 32781, Credentials: None

$ atvremote -n FakeATV playing
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off

$ atvremote -n FakeATV --protocol mrp pair
Enter PIN on screen: 1111
Pairing seems to have succeeded, yey!
You may now use these credentials: e734ea6c2b6257de7...
```

### Multiple Protocols

It is possible to use multiple protocols:

```shell
$ ./scripts/fake_device.py --mrp --dmap --airplay
Press ENTER to quit
```

And then scan for them:

```shell
$ atvremote scan
Scan Results
========================================
       Name: FakeATV
   Model/SW: 3 tvOS 13.x build 17K499
    Address: 127.0.0.1
        MAC: 40:CB:C0:12:34:56
Identifiers:
 - fakedev
 - 6D797FD3-3538-427E-A47B-A32FC6CF3A69
 - 00:01:02:03:04:05
Services:
 - Protocol: DMAP, Port: 40747, Credentials: 12345678-6789-1111-2222-012345678911
 - Protocol: MRP, Port: 40521, Credentials: None
 - Protocol: AirPlay, Port: 54472, Credentials: None
```

To interact with a particular protocol:

```shell
$ atvremote --id fakedev --protocol dmap playing
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off
```

### Demo Mode

There is a "demo mode" that changes between various things that are playing that can be enabled with `--demo`:

```shell
$ atvremote -n FakeATV playing
  Media type: Music
Device state: Paused
       Title: music
      Artist: artist
       Album: album
       Genre: genre
    Position: 22/49s (44.9%)
      Repeat: Off
     Shuffle: Off

$ atvremote -n FakeATV playing
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off
```

### Push Updates

Only `MRP` supports push update (`DMAP` get stuck in a loop):

```shell
$ atvremote -n FakeATV push_updates
Press ENTER to stop
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off
--------------------
  Media type: Video
Device state: Paused
       Title: dummy
    Position: 3/123s (2.4%)
      Repeat: Off
     Shuffle: Off
--------------------
  Media type: Music
Device state: Paused
       Title: music
      Artist: artist
       Album: album
       Genre: genre
    Position: 22/49s (44.9%)
      Repeat: Off
     Shuffle: Off
--------------------
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off
--------------------
```

### Play Media with AirPlay

There is very limited support for `AirPlay`. It is possible to "play" something, but it is just reported as "finished playing", so nothing really happens. But it is possible to call `play_url`:

```shell
$ atvremote --id fakedev --airplay-credentials 75FBEEC773CFC563:8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493 play_url=http://test
```

## Pairing

Some level of support for pairing is supported. Each section describes the limitations.

### MRP

More or less full support for pairing is supported. Credentials and PIN code are however hardcoded, so the process will always look the same:

```shell
$ atvremote --id fakedev --protocol mrp pair
Enter PIN on screen: 1111
Pairing seems to have succeeded, yey!
You may now use these credentials: e734ea6c2b6257de72355e472aa05a4c487e6b463c029ed306df2f01b5636b58:b7e8e084ca1a31dee7dd5fd0ddb1c4cacdc99f5aa0b27f178ecc34bd369c7ad2:35443739374644332d333533382d343237452d413437422d413332464336434633413639:62386265346261642d393338662d343765652d613735632d346238396666393134626430

$ atvremote --id fakedev --protocol mrp --mrp-credentials e734ea6c2b6257de72355e472aa05a4c487e6b463c029ed306df2f01b5636b58:b7e8e084ca1a31dee7dd5fd0ddb1c4cacdc99f5aa0b27f178ecc34bd369c7ad2:35443739374644332d333533382d343237452d413437422d413332464336434633413639:62386265346261642d393338662d343765652d613735632d346238396666393134626430 playing
  Media type: Unknown
Device state: Idle
      Repeat: Off
     Shuffle: Off
```

### DMAP

It is possible to initiate the pairing process with `DMAP`, but since verification is usually done on the Apple TV (PIN code is entered on the Apple TV), it is not possible to finish it. Should be easy to fix.

### AirPlay

Pairing is supported, but only with a specific set of credentials. This is because `AirPlay` lacks generic pairing support and just use a static pairing sequence. But it can be done like this:

```shell
$ atvremote --id fakedev --airplay-credentials 75FBEEC773CFC563:8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493 --protocol airplay pair
Enter PIN on screen: 2271
Pairing seems to have succeeded, yey!
You may now use these credentials: 75FBEEC773CFC563:8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493
```

### RAOP

Streaming files and most other feature should work to some extent. Encryption is not supported.

## State Support

Partial support for maintaining device state is implemented, but not for everything. Here is a simple example:

```shell
$ atvremote -n FakeMRP power_state
PowerState.On
$ atvremote -n FakeMRP turn_off
$ atvremote -n FakeMRP power_state
PowerState.Off
$ atvremote -n FakeMRP turn_on
$ atvremote -n FakeMRP power_state
PowerState.On
```

What is currently playing is currently configured per protocol but should be consolidated in the future (the same thing should be configured once and reported the same over all protocols).