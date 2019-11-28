---
layout: template
title: API
permalink: /development/api_reference/
link_group: development

files:
  - name: __init__.py
    description: Core functions for scanning, pairing and connecting.
  - name: conf.py
    description: Configuration and services.
  - name: const.py
    description: Various constants.
  - name: exceptions.py
    description: Exceptions that are specific to this library.
  - name: helpers.py
    description: A few convenience methods.
  - name: interface.py
    description: All the public interfaces.
---
# API Reference

At some point the API-reference will be listed here. In the meantime,
you can look at the source code of the modules:

| Filename | Content |
| -------- | ------- |
{% for file in page.files -%}
| [{{ file['name'] | replace: "__", "\_\_" }}]({{ "https://github.com/postlund/pyatv/blob/master/pyatv/" | append:file['name'] }}) | {{ file['description'] }} |
{% endfor- %}

The files above constitutes the public API. Any other file is to be considered
private and might change at any time with no further notice.