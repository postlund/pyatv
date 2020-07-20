---
layout: template
title: Migration
permalink: /support/migration/
link_group: support
---
# Migration

This page contains details on how to migrate between different versions
of `pyatv`. Beware that these guides are written according to "best effort"
and might be incomplete or missing some details. If you find something
to be unclear, please help out by writing an issue or creating a pull
request

## From 0.7.0 to 0.7.1

### General Changes

* Unicast scanning (i.e. passing `hosts` to `pyatv.scan`) will not verify
  if hosts are on the same network anymore (`NonLocalSubnetError` will not
  be thrown). Requests will just time out. See [#775](https://github.com/postlund/pyatv/issues/775)
  for more details.

### Deprecations

* `NonLocalSubnetError` is never thrown and shall not be checked for. It
  will be removed in 0.9.0.

## From 0.6.0 to 0.7.0

### General Changes

* No library changes
* MRP arguments to atvproxy has been simplified (only credentials and IP to
  Apple TV must now be provided)

### Deprecations

* None

## From 0.5.0 to 0.6.0

### General Changes

  * {% include api i="interface.AppleTV.close" %} has been changed to a
    regular function instead of a coroutine.
  * All listeners are now stored as weak references

## From 0.4.0 to 0.5.0

### General Changes

* None

### Deprecations

* Python 3.6 or later is now required
* `suspend` and `wakeup` in {% include api i="interface.RemoteControl" %}
  have been deprecated. Use {% include api i="interface.Power.turn_on" %}
  and {% include api i="interface.Power.turn_off" %} instead.
* {% include api i="helpers.auto_connect" %} is now a coroutine. The
  [example](https://github.com/postlund/pyatv/blob/master/examples/auto_connect.py)
  has been updated.

## From 0.3.x to 0.4.0

### General Changes

* Device configuration has moved from `AppleTVDevice` to `conf.AppleTV`
* `pyatv.connect_to_apple_tv` has been renamed to `pyatv.connect`
* `pyatv.scan_for_apple_tvs` has been renamed to `pyatv.scan`
* Pairing has been made generic and is done via `pyatv.pair`
* Constants, e.g. media type, has been changed into enums
* `play_state` has been renamed to `device_state`
* AirPlay interface has been renamed from `AppleTV.airplay` to `AppleTV.stream`

### Deprecations

* Arguments `abort_on_found` and `only_home_sharing` have been removed from `pyatv.scan`
* The `Metadata.artwork_url` method has been deprecated and has no
  replacement
* All methods in the AirPlay interface has been deprecated in favor
  of the generic pairing interface (except for `play_url`)
* `pyatv.pair_with_apple_tv` has been replaced by `pyatv.pair` which can pair all protocols
