---
layout: template
title: Acknowledgements
permalink: /support/acknowledgements/
link_group: support
---
# Acknowledgements

A *lot* of time and effort has been put into this project in order
to get where it is today. Some things I've done myself, but I could
of course not have done it all without help. So this page is a small
dedication the rest of you!

## External Projects

**[GitHub](https://github.com)**

Thanks for providing a good, integrated platform supporting free and
open source software. Since the launch of Pages and Actions I've
managed to move more or less completely to rely on GitHub services,
which is great!

**[mediaremotetv-protocol](https://github.com/jeanregisser/mediaremotetv-protocol)**

Thanks to Jean Regisser, which started exploring the Media Remote Protocol
and giving early insights. The `MRP` support is based on this findings.
It also helped me complete the reverse engineering of the protocol.
Some of my findings I have already submitted back.

**[pdoc3](https://pdoc3.github.io/pdoc/)**

Every library needs an API reference. I use pdoc3 for that due to its
flexibility. With some tweaks it integrates neatly with the rest of the
documentation.

**[miniaudio](https://github.com/mackron/miniaudio) / [pyminiaudio](https://github.com/irmen/pyminiaudio)**

Excellent minimalistic library for decoding and working with audio files! Supports
most relevant audio formats and operating systems. This library is vital
for audio streaming in RAOP (used via the python library).

## Contributors

This is a complete list of everyone that has contributed code to
the project: thank you!

```raw
acheronfail <acheronfail at gmail.com>
Alexandre Pulido <apulido at free.fr>
Alexey <alexey.www at gmail.com>
Andreas Billmeier <b at edevau.net>
Colin <12702068+ckeehan at users.noreply.github.com>
Colin <ckeehan at me.com>
crxporter <38265886+crxporter at users.noreply.github.com>
Dennis Frommknecht <dfrommi at users.noreply.github.com>
Doug Hoffman <doug+github at hoff.mn>
Erik Hendrix <hendrix_erik at hotmail.com>
jakobjjw <73580309+jakobjjw at users.noreply.github.com>
jdsnape <joel at sna.pe>
J. Nick Koston <nick at koston.org>
John Lian <jlian at users.noreply.github.com>
KibosJ <29429479+KibosJ at users.noreply.github.com>
Lucas Christian <lucas at lucasec.com>
Maximilian Leith <maximilian at leith.de>
Michael Carroll <mrc at apple.com>
Michał Modzelewski <michal.modzelewski at gmail.com>
Nebz <28622481+NebzHB at users.noreply.github.com>
Paul <itsascambutmailmeanyway at gmail.com>
Pierre Ståhl <pierre.sigma at renzgroup.com>
Pierre Ståhl <pierre.staahl at gmail.com>
Pierrick Rouxel <pierrick.rouxel at me.com>
Raymond Ha <raymond at shraymonks.com>
Robbie Trencheny <me at robbiet.us>
Rob Nee <robnee at hotmail.com>
sassukeuchiha <116432455+sassukeuchiha at users.noreply.github.com>
SchlaubiSchlump <Schlaubischlump at users.noreply.github.com>
Sebastian Pekarek <mail at sebbo.net>
Stackie Jia <jsq2627 at gmail.com>
stickpin <630000+stickpin at users.noreply.github.com>
stimulated <56211318+xpnewmedia at users.noreply.github.com>
Sylvain CECCHETTO <cecchetto.sylvain at me.com>
Will Ross <paxswill at paxswill.com>
```

*The list is manuallt updated, so if you are missing feel to send a
PR. The list is generated with:
`git log --format="%aN <%aE>" | sort | uniq | egrep -v "dependabot" |  sed -s 's/@/ at /'`*
