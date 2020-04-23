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
Similarly, ``playstatus_error`` is called if an error occur. See the
following example:

```python
class MyPushListener(interface.PushListener):

    def playstatus_update(self, updater, playstatus):
        # Currently playing in playstatus

    def playstatus_error(self, updater, exception):
        # Error in exception


listener = MyPushListener()
atv.push_updater.listener = listener
atv.push_updater.start()
```

Assuming the connection to the device is still active, push updates will
continue to be delivered after an error has happened. The parameter
`initial_delay` to `start` specifies the delay that should be used before
"trying to deliver updates again", but it might also be ignored if it is
deemed not necessary. The reason for its existence is purly to provide a
way to not hammer the device in case of errors.

## Device Updates

It is possible to get callbacks whenever a device loses its connection. Two methods
are used: one for expected loss, e.g. manually disconnecting and one for unexpected
loss, e.g. a crash or network problem. The API is defined by the
{% include api i="interface.DeviceListener" %} interface and works similarly to how push updates works.

Here is a simple example:

```python
class MyDeviceListener(interface.DeviceListener):

    def connection_lost(self, exception):
        print("Lost connection:", str(exception))

    def connection_closed(self):
        print("Connection closed!")


listener = MyDeviceListener()
atv.listener = listener
```

A small note here about this API. For `MRP` this works fine as that protocol
is connection oriented. It's another case for `DMAP`, since that protocol is
request based. For now, this interface is implemented by the push updates
API (to be clear: for `DMAP`). So when the push updates API fails to establish
a connection, the callbacks in this interface will be called.

## Power State Updates

It is possible to get callbacks whenever a device power state is changed, 
e.g. the device turned on or turned off. The API is defined by the
 {% include api i="interface.PowerListener" %} interface and works similarly to how push updates works.

Here is a simple example:

```python
class MyPowerListener(interface.PowerListener):

    def powerstate_update(self, old_state, new_state):
        print('Power state changed from {0:s} to {1:s}'.format(old_state, new_state))


listener = MyPowerListener()
atv.power.listener = listener
```

A small note here about this API. Power state updates are working for `MRP` devices
only.
