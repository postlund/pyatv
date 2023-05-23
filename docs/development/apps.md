---
layout: template
title: Apps
permalink: /development/apps/
link_group: development
---
# Apps

It is possible to launch and list installed apps via the Apps interface.
To use this interface, the Companion protocol must be available.

## Using the Apps API

After connecting to a device, you get the apps interface via {% include api i="interface.AppleTV.apps" %}:

```python
atv = await pyatv.connect(config, ...)
apps = atv.apps
```

To retrieve a list of installed apps, use {% include api i="interface.Apps.app_list" %}

```python
app_list = await apps.app_list()

for app in app_list:
    print(f"Name: {app.name}, Bundle Identifier: {app.identifier}")
```

To launch an app, use its bundle identifier when calling {% include api i="interface.Apps.launch_app" %}

 ```python
await apps.launch_app("com.netflix.Netflix")
 ```

To launch an app with a URL, pass the URL when calling {% include api i="interface.Apps.launch_app" %}

 ```python
await apps.launch_app("com.apple.tv://tv.apple.com/show/marvels-spidey-and-his-amazing-friends/umc.cmc.3ambs8tqwzphbn0u8e9g76x7m?profile=kids&action=play")
 ```