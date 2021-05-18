---
layout: template
title: Features
permalink: /development/features/
link_group: development
---
# Features

It is possible to obtain information about available features of a device, e.g. if it supports playback actions or power management, using {% include api i="interface.Features" %}. Supported features are listed in {% include api i="const.FeatureName" %}.

## Feature State

A feature can at any given time be considered to be in one of the following states:

| State | Meaning |
| ----- | ------- |
| Unknown | The feature is supported by the device but it is not possible to determine if it is available or not, i.e. if it can be used *now*. All devices for instance supports `Pause`, but it is only possible to pause if something is playing.
| Unsupported | The feature is not supported by the device at all, e.g. Siri is unsupported on Apple TV 3 *or* none of the configured protocols support this feature.
| Unavailable | The feature is supported but currently not possible to use, e.g. skip to next track is only possible if a song is playing.
| Available | The feature is supported and available now, e.g. `Pause` is possible because something is playing.

Because of technical reasons, the state of some features are not possible to determine, so pyatv will make an educated guess. If something seems strange, please write an [issue](https://github.com/postlund/pyatv/issues/new?assignees=&labels=bug&template=bug_report.md&title=) about it. Make sure you include full debug logs, otherwise it will be hard to troubleshoot.

## Using the Features API

After connecting to a device, you get the interface via {% include api i="interface.AppleTV.features" %}:

```python
atv = await pyatv.connect(config, ...)
ft = atv.features
```

To obtain current state of a feature, e.g. {% include api i="const.FeatureName.Play" %}, use {% include api i="interface.Features.get_feature" %}:

```python
from pyatv.const import FeatureName, FeatureState

info = ft.get_feature(FeatureName.Play)
if info.state == FeatureState.Available:
    await atv.remote_control.play()
else:
    print("Play is not possible right now")
```

The state of all features can be obtained via {% include api i="interface.Features.all_features" %}. By default, this method will exclude unsupported features. Pass `include_unsupported=True` when calling to include state of all features:

```python
all_features = ft.all_features(include_unsupported=unsupported)
for name, feature in all_features.items():
    print(f"{name} = {feature.state}")
```

There's a helper method, {% include api i="interface.Features.in_state" %}, that checks if one or
more features are in one or several states:

```python
# Check if Play is available
if ft.in_state(FeatureState.Available, FeatureName.Play):
    pass

# Check if Play is either available or unsupported
if ft.in_state([FeatureState.Available, FeatureState.Unsupported],
               FeatureName.Play):
    pass

# Check if Play *and* Pause are supported
if not ft.in_state(FeatureName.Unsupported, FeatureName.Play, FeatureName.Pause):
    pass

```