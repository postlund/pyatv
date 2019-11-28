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
  - name: scan_and_connect.py
    description: Scans for devices, picks the first one and connects to it.
---
# Examples

There are a few example bundled with `pyatv` in the `examples` subdirectory:

| Filename | Description |
| -------- | ----------- |
{% for file in page.files -%}
| [{{ file['name'] | replace: "__", "\_\_" }}]({{ "https://github.com/postlund/pyatv/blob/master/examples/" | append:file['name'] }}) | {{ file['description'] }} |
{% endfor- %}

More examples can be added on request, please write an
[issue](https://github.com/postlund/pyatv/issues/new?assignees=&labels=question&template=question-or-idea.md&title=)
if you want something more specific.