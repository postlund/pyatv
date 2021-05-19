---
layout: template
title: Audio
permalink: /development/audio/
link_group: development
---
# Audio

Protocols supporting volume controls can be controlled via the audio interface.

**No protocol currently implement this interface!**

## Using the Audio API

After connecting to a device, you get the apps interface via {% include api i="interface.AppleTV.audio" %}:

```python
atv = await pyatv.connect(config, ...)
audio = atv.audio
```

To get current volume level, use {% include api i="interface.Audio.volume" %}:

```python
print("Volume:", audio.volume)
```

To change current volume, use {% include api i="interface.Audio.set_volume" %}:

```python
audio.set_volume(20.0)
```

The volume level is normalized in the interval 0.0-100.0, where 0.0 means
the audio is muted.
