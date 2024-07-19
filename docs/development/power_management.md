---
layout: template
title: Power Management
permalink: /development/power_management/
link_group: development
---
# Power Management

Power management of a device is done with the power interface,
{% include api i="interface.Power" %}. It allows you to turn on, turn off and get current
power state. This interface is currently only supported by devices running tvOS.

## Using the Power Management API

After connecting to a device, you get the power management via {% include api i="interface.AppleTV.power" %}:

```python
atv = await pyatv.connect(config, ...)
pwrc = atv.power
```

You can then control via the available functions:

```python
await pwrc.turn_on()
await pwrc.turn_off()
```

To get current power state use following property:

```python
@property
def power_state(self) -> const.PowerState:
```

## Waiting for State Change

It is possible to pass `await_new_state` set to `True` when turning on
or off a device to have pyatv wait for a state change. E.g. calling
{% include api i="interface.Power.turn_off" %} will block until the device
has powered off:

```python
await pwrc.turn_off(await_new_state=True)
```

If the device is already off, it will return immediately.

To not block indefinitely, use `wait_for` with a timeout:

```python
await asyncio.wait_for(pwrc.turn_off(await_new_state=True), timeout=5)
```
