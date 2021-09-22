---
layout: template
title: Migration
permalink: /support/migration/
link_group: support
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# Migration

This page contains details on how to migrate between different versions
of pyatv. Beware that these guides are written according to "best effort"
and might be incomplete or missing some details. If you find something
to be unclear, please help out by writing an issue or creating a pull
request

# From 0.8.2-0.9.0

## General Changes

* To restore support with tvOS 15, make sure to provide AirPlay credentials. Credentials obtained with earlier versions of pyatv are incompatible (pair again).
* The `password` property previously present in `conf.RaopService` is now part of `interface.BaseService` instead.
* Make sure to verify {% include api i="interface.BaseService.pairing" %} before calling {% include api i="pyatv.pair" %} (in case new credentials are needed).
* Check {% include api i="interface.BaseService.requires_password" %} if a password needs to be provided
* At least version 3.17.3 of {% include pypi package="protobuf" %} is now required.
* {% include pypi package="mediafile" %} replaced {% include pypi package="audio-metadata" %} as a dependency

## Deprecations

* Service specific configurations, e.g. {% include api i="conf.MrpService" %}, have been replaced by {% include api i="conf.ManualService" %}. Scheduled for removal in 1.0.0.
* {% include api i="interface.RemoteControl.volume_up" %} and {% include api i="interface.RemoteControl.volume_down" %} are now replaced by {% include api i="interface.Audio.volume_up" %} and {% include api i="interface.Audio.volume_up" %}. Scheduled for removal in 1.0.0.

# From 0.7.1-... to 0.8.0

## General Changes

* The push updater interface is now considered a feature and availability
  (via {% include api i="interface.Features.get_feature" %} and
  {% include api i="const.FeatureName.PushUpdates" %}) should now be performed
  before using it.
* {% include pypi package="audio-metadata" %}, {% include pypi package="bitarray" %}
  and {% include pypi package="miniaudio" %} are new dependencies in this
  release (used by RAOP).
* At least version 3.14 of {% include pypi package="protobuf" %} is now required.

## Deprecations

* Passing `protocol` to {% include api i="pyatv.connect" %} is no longer
  needed and its value will be ignored. Scheduled for removal in version 1.0.0.

# From 0.7.0 to 0.7.1

## General Changes

* Unicast scanning (i.e. passing `hosts` to {% include api i="pyatv.scan" %}) will
  not verify if hosts are on the same network anymore (`NonLocalSubnetError` will
  not be thrown). Requests will just time out. See {% include issue no="775" %}
  for more details.

## Deprecations

* `NonLocalSubnetError` is never thrown and shall not be checked for. It
  will be removed in 0.9.0.

# From 0.6.0 to 0.7.0

## General Changes

* No library changes
* MRP arguments to atvproxy has been simplified (only credentials and IP to
  Apple TV must now be provided)

## Deprecations

* None

# From 0.5.0 to 0.6.0

## General Changes

  * {% include api i="interface.AppleTV.close" %} has been changed to a
    regular function instead of a coroutine.
  * All listeners are now stored as weak references

# From 0.4.0 to 0.5.0

## General Changes

* None

## Deprecations

* Python 3.6 or later is now required
* `suspend` and `wakeup` in {% include api i="interface.RemoteControl" %}
  have been deprecated. Use {% include api i="interface.Power.turn_on" %}
  and {% include api i="interface.Power.turn_off" %} instead.
* {% include api i="helpers.auto_connect" %} is now a coroutine. The
  [example](https://github.com/postlund/pyatv/blob/master/examples/auto_connect.py)
  has been updated.

# From 0.3.x to 0.4.0

## General Changes

* Device configuration has moved from `AppleTVDevice` to {% include api i="conf.AppleTV" %}
* `pyatv.connect_to_apple_tv` has been renamed to {% include api i="pyatv.connect" %}
* `pyatv.scan_for_apple_tvs` has been renamed to {% include api i="pyatv.scan" %}
* Pairing has been made generic and is done via {% include api i="pyatv.pair" %}
* Constants, e.g. media type, has been changed into enums
* `play_state` has been renamed to `device_state`
* AirPlay interface has been renamed from `AppleTV.airplay` to
  {% include api i="interface.AppleTV.stream" %}

## Deprecations

* Arguments `abort_on_found` and `only_home_sharing` have been removed from
  {% include api i="pyatv.scan" %}
* The `Metadata.artwork_url` method has been deprecated and has no
  replacement
* All methods in the AirPlay interface has been deprecated in favor
  of the generic pairing interface (except for `play_url`)
* `pyatv.pair_with_apple_tv` has been replaced by {% include api i="pyatv.pair" %}
  which can pair all protocols
