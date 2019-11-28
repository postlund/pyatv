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