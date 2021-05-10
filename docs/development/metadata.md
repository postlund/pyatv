---
layout: template
title: Metadata
permalink: /development/metadata/
link_group: development
---
# Metadata

It is possible to get metadata, i.e. what is playing, using two different
methods:

* Manually polling
* Push updates

Polling metadata from the device works very similar to the remote control
API, but one asynchronous call will return an object containing all metadata.
This is to lower the amount of device calls needed. Artwork is retrieved
separately.

When using push updates, new updates are *pushed* from the Apple TV when
something of interest happens. The exact same data that is available when
polling, is passed to a callback provided by the API user.

Push updates are described further in the [Listeners](../listeners) section.

## Currently playing

To retrieve what is currently playing, use the asynchronous playing method:

```python
playing = await atv.metadata.playing()
```

You can easily extract fields like title, album or media type. See
{% include api i="interface.Playing" %}.

Support by protocol (assuming app sets metadata correctly):

* MRP: All fields
* DMAP: All except {% include api i="interface.Playing.series_name" %},
  {% include api i="interface.Playing.season_number" %} and {% include api i="interface.Playing.episode_number" %}
* AirPlay and Companion: None

## Artwork

To retrieve the artwork, use the asynchronous artwork method:

```python
artwork = await atv.metadata.artwork()
```

This will return an {% include api i="interface.ArtworkInfo" %}, containing the image bytes,
mimetype and dimensions. If no artwork is available, `None` is returned instead. If dimensions
could not be determined by the device, `width` and `height` will be set to -1.

It is also possible to request artwork with a particular size by passing `width` and `height`:

```python
artwork = await atv.metadata.artwork(width=300, height=200)
```

Do note that this is the desired size and the device might return artwork with another size,
e.g. to keep aspect ratio or if specified size it not available. You can pass `None` as one
of the arguments to let the device maintain aspect ratio of the image.

Remember that the artwork is relatively large, so you should try to minimize
this call. More information is available at  {% include api i="interface.Metadata.artwork" %}.
Internally, a small cache is used for the last few requested artworks. The size of this cache
is not yet configurable and you should write a feature request if you need to change it.

## Device identifier

The concept of *unique identifiers* was discussed in the
[concepts](../../documentation/concepts/#identifiers) section. You can retrieve one of the
identifiers via this property:

```python
identifier = atv.metadata.device_id
```

## Hash

To simplify detection if content has changed between retrieval of what is
currently playing, a unique hash can be generated. It is a SHA256 hash based
on the following data:

- Title
- Artist
- Album
- Total time

These properties has been selected as they are in general unique for the same
content. No guarantee is however given that the same hash is not given for
different content nor the same content. It can be used as a fair guess.

```python
playing = await atv.metadata.playing()
...  # Some time later
playing2 = await atv.metadata.playing()
if playing2.hash != playing.hash:
    print('Content has changed')
```

## Active App

Is is possible to get information about the app that is currently playing something via
 {% include api i="interface.Metadata.app" %}:

```python
app = atv.metadata.app
print("Name:", app.name)
print("Identifier:", app.identifier)
```

It conforms to the  {% include api i="interface.App" %} interface.
