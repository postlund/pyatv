---
layout: template
title: Device Information
permalink: /development/device_info/
link_group: development
---
# Device Information

pyatv can extract various information about a device, e.g. which
operating system (and version) it runs or its hardware model (3, 4K, etc.).
This information is exposed via the interface {% include api i="interface.DeviceInfo" %}.

## Using the Device Information API

After connecting to a device, you get device info via {% include api i="interface.AppleTV.device_info" %}:

```python
atv = await pyatv.connect(config, ...)
devinfo = atv.device_info
```

You can then access the actual information via properties:

```python
print(devinfo.operating_system)
print(devinfo.version)
print(devinfo.mac)
```

 Just printing `devinfo` will produce a summary of the device information
 (MAC-address is not included here):
 
 ```python
 >>> print(devinfo)
 4K tvOS 13.3.1 build 17K795
 ```