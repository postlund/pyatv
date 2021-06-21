---
layout: template
title: Examples
permalink: /development/examples/
link_group: development

files:
  - name: auto_connect.py
    description: Demonstrates the simple `auto_connect` helper.
  - name: manual_connect.py
    description: Manual creation of a configuration used to connect to a device.
  - name: pairing.py
    description: Generic example demonstrating the pairing API.
  - name: play_url.py
    description: Play a video from URL using AirPlay.
  - name: scan_and_connect.py
    description: Scans for devices, picks the first one and connects to it.
  - name: stream.py
    description: Stream audio file to an AirPlay/RAOP receiver.
  - name: tutorial.py
    description: Complete source code of [tutorial](../../documentation/tutorial).
---
# Examples

There are a few example bundled with pyatv in the `examples` subdirectory:

| Filename | Description |
| -------- | ----------- |
{% for file in page.files -%}
| [{{ file['name'] | replace: "__", "\_\_" }}]({{ "https://github.com/postlund/pyatv/blob/master/examples/" | append:file['name'] }}) | {{ file['description'] }} |
{% endfor- %}

These scripts that are bundled with pyatv can be used for inspiration as well:

* [atvremote](https://github.com/postlund/pyatv/blob/master/pyatv/scripts/atvremote.py)
* [atvscript](https://github.com/postlund/pyatv/blob/master/pyatv/scripts/atvscript.py)

More examples can be added on request, please write an
[issue](https://github.com/postlund/pyatv/issues/new?assignees=&labels=question&template=question-or-idea.md&title=)
if you want something more specific.