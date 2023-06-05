---
layout: template
title: Keyboard
permalink: /development/keyboard/
link_group: development
---
# Keyboard

It is possible to interact with the Apple TV virtual keyboard via the Keyboard interface.
To use this interface, the Companion protocol must be available.

## Using the Keyboard API

After connecting to a device, you get the keyboard interface via {% include api i="interface.AppleTV.keyboard" %}:

```python
atv = await pyatv.connect(config, ...)
keyboard = atv.keyboard
```

To check whether the virtual keyboard is focused and active, use {% include api i="interface.Keyboard.text_focus_state" %}:

```python
print("Keyboard focus state:", keyboard.text_focus_state)
```

To fetch the current virtual keyboard text content, use {% include api i="interface.Keyboard.text_get" %}:

```python
print("Keyboard text:", await keyboard.text_get())
```

To set (replace) the virtual keyboard text, use {% include api i="interface.Keyboard.text_set" %}:

```python
await keyboard.text_set("text to set")
```

To append to the virtual keyboard text, use {% include api i="interface.Keyboard.text_append" %}:

```python
await keyboard.text_append("text to append")
```

Finally, to clear the virtual keyboard text, use {% include api i="interface.Keyboard.text_clear" %}:

```python
await keyboard.text_clear()
```

The keyboard API supports push updates via a listener, as described [here](../listeners#keyboard-updates).
