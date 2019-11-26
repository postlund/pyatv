---
layout: template
title: Listeners
permalink: /development/listeners/
link_group: development
---
# Listeners

In some cases it's not appropriate to contiuously poll the device for information.
What is currently playing should be updated instantly for instance. This is supported
via callbacks using a `listener`.

## Push Updates

The push update API is based on a regular callback interface. When playstatus
information is available, a method called ``playstatus_update`` is called.
Similarily, ``playstatus_error`` is called if an error occur. See the
following example:

```python
class PushListener:

    def playstatus_update(self, updater, playstatus):
        # Currently playing in playstatus

    def playstatus_error(self, updater, exception):
        # Error in exception


listener = PushListener()
atv.push_updater.listener = listener
atv.push_updater.start()
```

Assuming the connection to the device is still active, push updates will
continue to be delivered after an error has happened. The paramater
`initial_delay` to `start` specifies the delay that should be used before
"trying to deliver updates again", but it might also be ignored if it is
deemed not necessary. The reason for its existence is purly to provide a
way to not hammer the device in case of errors.

## Device Updates

It is possible to get callbacks whenever a device loses its connection. Two methods
are used: one for expected loss, e.g. manually disconnecting and one for unexpected
loss, e.g. a crash or network problem. The API is defined by the
`interface.DeviceLister` interface and works similarily to how push updates works.

Here is a simple example:

```python
class DeviceListener:

    def connection_lost(self, exception):
        print("Lost connection:", str(exception))

    def connection_closed(self):
        print("Connection closed!")


atv.listener = DeviceListener()
```

A small note here about this API. For `MRP` this works fine as that protocol
is connection oriented. It's another case for `DMAP`, since that protocol is
request based. For now, this interface is implemented by the push updates
API (to be clear: for `DMAP`). So when the push updates API failes to establish
a connection, the callbacks in this interface will be called.
