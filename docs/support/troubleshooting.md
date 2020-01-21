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


### I can't enter leading zeros for my PIN

Enter your PIN without the leading zeros, and they'll be added automatically
to create a4-digit PIN. For example, if your PIN is "0123" enter "123".
If your PIN is "0007", just enter "7".

This approach ensures you don't accidentally enter characters (or your password)
in this box. 


### No PIN code is displayed when I try to pair with AirPlay

First check that you've got Apple TV assigned to a "room" in the correct HomeKit
home. Go to Settings, Airplay and Homekit, and make sure that "Room" has a valid
value assigned. Then retry pairing.

If no screen is displayed with the PIN code, try navigating to the AirPlay
settings menu on your Apple TV. The code should be visible there.


### The exception "pyatv.exceptions.DeviceAuthenticationError: pair start failed" is thrown when I try to pair with AirPlay

Make sure you have *Allow Access* set to *Anyone on the Same Network* for
AirPlay on your Apple TV. For details, see issue [#377](https://github.com/postlund/pyatv/issues/377).
