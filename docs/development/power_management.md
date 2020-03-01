---
layout: template
title: Power Management
permalink: /development/power_management/
link_group: development
---
# Power Management

Power management of a device is done with the power interface,
`interface.Power`. It allows you to turn on, turn off and get current
power state.

List of supported devices:
 - Apple TV Gen 4
 - Apple TV 4K

## Using the Power Management API

After connecting to a device, you get the power management via `power`:

```python
atv = await pyatv.connect(config, ...)
pwrc = atv.power
```

You can then control via the available functions:

```python
await pwrc.turn_on()
await pwrc.turn_off()
```

To get current power state use following function:

```python
@property
def power_state(self):
```

