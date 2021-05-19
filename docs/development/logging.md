---
layout: template
title: Logging
permalink: /development/logging/
link_group: development
---
# Logging

In case you need to troubleshoot something, you can enable additional log points in pyatv.
This page describes how you do that.

# Log points

To enable full logging, use this:

```python
logging.basicConfig(
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
    format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
)
```

This output format is preferred as it is compatible with [atvlog](../../documentation/atvlog) and
contains the most useful information.

In case you need to troubleshoot MDNS/Zeroconf traffic, use this:

```python
logging.getLogger(
    "pyatv.support.mdns"
).level = logging.TRAFFIC  # pylint: disable=no-member
```

*NOTE: This section is WIP for now as most interesting log points are internal. In the future,
a `log` module will be added to simplify enabling log points.*

# Bundled scripts

You can enable additional debugging information by specifying either `--verbose` or `--debug.`.

# Output line cropping

By default pyatv will limit some log points in length, mainly due to an excessive amount of
data might be logged otherwise. This mainly applies to binary data (raw protocol data) and
protobuf messages. These limits can be overridden by setting the following environment variables:

```shell
$ export PYATV_BINARY_MAX_LINE=1000
$ export PYATV_PROTOBUF_MAX_LINE=1000
$ atvremote --debug ... playing
```

In general, you shouldn't have to change these, but under some cicrumstances the complete
logs might be deseriable.
