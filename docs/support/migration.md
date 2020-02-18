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
request.

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
