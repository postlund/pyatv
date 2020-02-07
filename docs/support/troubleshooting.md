---
layout: template
title: Troubleshooting
permalink: /support/troubleshooting/
link_group: support
---
# Troubleshooting

If you are having problems, have a look at this page. There are currently not
much content here, please submit a PR or write an issue if you want to add or
change something.

### Scanning does not find any devices

Please see [this](../scanning_issues/) page on scanning issues.

### No PIN code is displayed when I try to pair with AirPlay

If no screen is displayed with the PIN code, try navigating to the AirPlay
settings menu on your Apple TV. The code should be visible there.

### The exception "pyatv.exceptions.DeviceAuthenticationError: pair start failed" is thrown when I try to pair with AirPlay

Make sure you have *Allow Access* set to *Anyone on the Same Network* for
AirPlay on your Apple TV. For details, see issue [#377](https://github.com/postlund/pyatv/issues/377).

### How do I get additional logs that I can attach when creating an issue?

You can pass `--debug` to `atvremote` to get extensive debug logs. For more details, see
the [atvremote](../../documentation/atvremote) page.
