---
layout: template
title: Troubleshooting
permalink: /support/troubleshooting/
link_group: support
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# Scanning does not find any devices

Please see [this](../scanning_issues/) page on scanning issues.

# No PIN code is displayed when I try to pair with AirPlay

First check that you've got Apple TV assigned to a "room" in the correct HomeKit
home. Go to Settings, Airplay and Homekit, and make sure that "Room" has a valid
value assigned. Then retry pairing.

If no screen is displayed with the PIN code, try navigating to the AirPlay
settings menu on your Apple TV. The code should be visible there.

# The exception "pyatv.exceptions.DeviceAuthenticationError: pair start failed" is thrown when I try to pair with AirPlay

Make sure you have *Allow Access* set to *Anyone on the Same Network* for
AirPlay on your Apple TV. For details, see issue {% include issue no="377" %}.

# How do I get additional logs that I can attach when creating an issue?

You can pass `--debug` to `atvremote` to get extensive debug logs. For more details, see
the [atvremote](../../documentation/atvremote) page.

# I do not receive updates in my listeners, e.g. when media state changes

From version 0.6.0 of pyatv, *weak references* are kept to all listeners. This means that if a listener
is not "reachable" from outside of pyatv, it will be garbage collected the next time the garbage
collector runs. A typical situation when this would happen looks like this:

```python
class DummyPushListener:
    @staticmethod
    def playstatus_update(updater, playstatus):
        pass

    @staticmethod
    def playstatus_error(updater, exception):
        pass

self.atv.push_updater.listener = DummyPushListener()
self.atv.push_updater.start()
```

In this case, no one else has a reference to the instance of `DummyPushListener` (other than pyatv), so
it will be freed when the garbage collector runs (which can be at any given time). Changing the code into
this would work better:


```python
listener = DummyPushListener()
self.atv.push_updater.listener = listener
self.atv.push_updater.start()
```

Here a local reference is kept to the listener. Beware that the same issue will arise when `listener`
goes out of scope, so make sure all your listeners live at least as long as they are used in pyatv.
