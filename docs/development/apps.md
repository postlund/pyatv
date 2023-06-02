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
await apps.launch_app("https://tv.apple.com/show/marvels-spidey-and-his-amazing-friends/umc.cmc.3ambs8tqwzphbn0u8e9g76x7m?profile=kids&action=play")
 ```

### App deep links

tvOS, allows deep linking into apps. So the {% include api i="interface.Apps.launch_app" %} API is very powerful for
navigating content on the Apple TV.

Here are some known working examples:
* https://tv.apple.com/show/severance/umc.cmc.1srk2goyh2q2zdxcx605w8vtx
* https://www.disneyplus.com/series/the-beatles-get-back/7DcWEeWVqrkE
* https://play.hbomax.com/page/urn:hbo:page:GXkRjxwjR68PDwwEAABKJ:type:series
* https://www.netflix.com/title/80234304

The simplest way to find useful deep links is to use the "Share" feature in iOS or macOS versions of the App. Share 
sheets will often have a "Copy" or "Copy link" feature. For apps that have a web accessible version, links copied from
the browser usually work too (this is how iOS handles linking into apps from web links).

Sometimes a link copied this way will not work, but can be made to work with a slight modification, e.g. removing a 
country code from the URL.

If this approach fails, you can inspect the app to discover insights about supported URLs. The recommended way to 
support [app links](https://developer.apple.com/documentation/xcode/allowing-apps-and-websites-to-link-to-your-content)
is by defining
[associated domains](https://developer.apple.com/documentation/xcode/allowing-apps-and-websites-to-link-to-your-content).

To discover domains associated with an app, list the app entitlements, then search for `associated-domains` within 
the output. You can do this using the `codesign` tool on macOS.
```bash
$ codesign -d --entitlements - "/path/to/Interesting.app/"
```

Once potential domains are identified you can check the content of the file hosted at  
`https://<domain>/.well-known/apple-app-site-association`. This is a file that is required to be hosted to support 
associated domains, and contains patterns matching URLs that the app claims to support. Check out some examples from
[Disney+](https://www.disneyplus.com/.well-known/apple-app-site-association) and
[Netflix](https://www.netflix.com/.well-known/apple-app-site-association).

Some apps also define a
[custom URL scheme](https://developer.apple.com/documentation/xcode/defining-a-custom-url-scheme-for-your-app), which
is an alternative API for supporting app links. These can be inspected by looking at
`/path/to/Interesting.app/Info.plist` or
`/path/to/Interesting.app/Contents/Info.plist` and searching for CFBundleURLSchemes.
