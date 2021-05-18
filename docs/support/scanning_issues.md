---
layout: template
title: Scanning Issues
permalink: /support/scanning_issues/
link_group: support
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# Scanning Issues

Scanning for devices relies on the [Zeroconf](https://en.m.wikipedia.org/wiki/Zero-configuration_networking)
technology stack. Simplified (and technically) it means that zeroconf devices acts
as DNS servers and listens to requests on a specific multicast address (also using
port 5353 instead of regular 53). When someone wants to find devices supporting a
particular service, it sends a DNS request to the multicast address (on port 5353)
and await response from other devices. This is an *extremely* simplified view of
what is going on.

There are a number of sources of errors to consider:

* Firewalls or routers block multicast traffic
* Timing issues: responses not received in time
* Responses filtered by kernel (or somewhere else), not received in application

The latter two seems to be most common. Lets break them down.

# Timing issues

Timing issues can happen because pyatv only scans for a small period of time. By
saying "scan", we actually mean sending out requests and waiting for responses. The
wait time should be long enough to receive all responses but short enough to not be
annoying to the user. Waiting five minutes for a scan to finish *is* annoying. By
default, pyatv scans for 3 seconds (with `atvremote`).

Not receiving responses within the time frame obviously is problematic. To make the
matter even more complex: pyatv relies upon several services. One for `MRP`,
one for AirPlay and so on. They are requested *independently* of each other. This
means that it is possible to get a response for AirPlay but miss `MRP` because of
timing issues (or other issues as well). You might see this happen sometimes when
scanning, that one or more service is missing. This is the reason why that happens.

# Response filtering

A behavior that has been observed is that the response is indeed received by the host
(as seen with Wireshark), but it is never forwarded to the python process so `zeroconf`
never receives it. Some filtering happens at some point for some reason. It is still
unclear if this is a bug in python or not and should be investigated further.

# Working around issues

Issues with scanning has always plauged pyatv and it still does. To mitigate the
problems, support for "unicast scanning" has been added. It is meant as a compliment
to regular scanning, as it cannot replace that.

Unicast scanning (which is an expression used here, it is not a commonly accepted term)
works in the same way as regular multicast but the request is sent to specific hosts instead.
You basically say: "scan *these* IP-addresses". This seems to work more relibly and it also
comes with some other advantages:

* It is fast because we know exactly which answers to wait for
* All services can be obtained with *one* request, so no timing issues
* All data pyatv requires, like unique identifiers, are present so it is more reliable than manual configuration

Support for unicast scanning has been added via the `--scan-hosts` flag in `atvremote`.

# Troubleshooting further

If pyatv doesn't find your devices, you can try other Zeroconf tools to see if it is
a general issue or not.

For Linux:

    $ avahi-browse --all

For macOS:

    $ dns-sd -B _appletv-v2._tcp.
    OR
    $ dns-sd -G -B _touch-able._tcp.
    OR
    $ dns-sd -G -B _mediaremotetv._tcp.

If you get an error such as "command not found", you do do not have avahi
installed. You will have to consult your distributions support channels
(e.g. forum) for help on this.

Here are some other possible sources of problems:

- Bonjour/Zeroconf requires you to be on the same network as the devices
  you are looking for. This means that you cannot scan for devices from
  inside of a container or virtual machine, unless they are using a bridged
  network interface.
- If you are running a Mac or using an iPhone, try enabling AirPlay mirroring
  or use the Remote app. Unless you can get that to work, it is highly
  unlikely that pyatv will work either.
- If you can see your Apple TV on your iPhone, you can try to install an app
  suitable for Bonjour discovery. Just search for *bonjour* in the App store
  (there might be alternatives for Android as well) and lool for your device.
  If it's not found then pyatv will likely not fins it either.
- Firewalls might block the necessary traffic for Bonjour. Make sure the
  traffic is allowed or disable it when scanning.
- We have seen that switching the Apple TV from WiFi to cable solves the problem
  in some cases. It is recommended that you try it out.

If you continue having problems scanning for devices, consider writing a
[support issue](https://github.com/postlund/pyatv/issues/new?assignees=&labels=question&template=question-or-idea.md&title=).
Remember to include debug logs (`--debug` if you are using `atvremote`).