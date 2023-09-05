---
layout: template
title: Storage and Settings
permalink: /development/storage/
link_group: development
---
 Table of Contents
{:.no_toc}
* TOC
{:toc}

# Storage and Settings

The storage API provides a way to store and read settings persistently, e.g. in a local file or remotely
on a cloud service. Settings include things such as:

* Various metadata, e.g. remote name, MAC address
* Credentials and passwords for services
* Protocol specific settings, e.g. port numbers

As storage is still a new API, only a handful settings are supported at the time of writing. More settings
will be added over time. To request a new setting, please open a new issue.

## Available Storage Modules

The following storage modules are shipped with pyatv:

| **Module** | **Description** | **API** |
| MemoryStorage | Stores settings within an instance in memory and are discarded when the object is no longer referenced. | {% include api i="storage/memory_storage.MemoryStorage" %}
| FileStorage | Stores settings in a file in JSON format. | {% include api i="storage/file_storage.FileStorage" %}
| AbstractStorage | Base class to ease development of custom storage modules, see [here](#custom-storage-module). | {% include api i="storage.AbstractStorage" %}

All main methods in `pyatv` ({% include api i="pyatv.connect" %}, {% include api i="pyatv.scan" %} and
{% include api i="pyatv.pair" %}) accept `storage` as an argument. Typically a storage instance is created once
and are then passed on to all mentioned methods. If no storage module is provided, a
{% include api i="storage/memory_storage.MemoryStorage" %} instance is created internally and used for storage.

## Storage Guidelines

When using the storage API, there are a few guidelines to consider:

* All settings are device specific
* If a setting is not set, a default value is used (see {% include api i="settings" %} for values)
* Settings are generally not changed after {% include api i="pyatv.connect" %} has been called

The gist is more or less that settings are independent on device level (you can set different MAC addresses
per device for instance) and they apply instantly. It is however not certain that it will be used until the
next {% include api i="pyatv.connect" %} call, since many settings are only used when connecting.

Internally, `pyatv` will automatically populate the provided storage with new devices when scanning and also
insert credentials when pairing. Once a protocol has been successfully paired, no further credential
management is necessary as the credentials will be available via the storage.

Settings are managed via an instance of {% include api i="settings.Settings" %}, typically available via
{% include api i="interface.AppleTV.settings" %}. It is also possible to retrieve settings directly from
storage using {% include api i="interface.Storage.get_settings" %}.

*Note: All changes made to a storage are stored in memory only until
{% include api i="interface.Storage.save" %} is called. Make sure to call this method after all
relevant updates, otherwise they will be lost!*

## Settings Priority

Storage is treated as a "first-class citizen" in pyatv. This means that internally, whenever pyatv
needs settings for a configuration, it will load whatever is in storage and overwrite what is currently
set in the configuration. If a setting is not present in storage, the corresponding setting in the
configuration will however remain unchanged.

The practical way of thinking about this is that settings and configurations are modified independently,
i.e. you can change a setting in storage to one value and corresponding setting in the configuration to
another value, thus creating an inconsistency. However, when you call a pyatv method, e.g.
{% include api i="pyatv.connect" %}, settings will be loaded from storage and overwrite whatever is
set in the configuration. Here is a simple example illustrating this:

```python
storage = FileStorage("pyatv.conf", loop)

conf = await pyatv.scan(loop, identifier="xxx")[0]    # Scan without storage
conf.get_service(Protocol.AirPlay).password ="pyatv"  # Change something in configuration

settings = await storage.get_settings(conf)           # "conf" does not exist in this storage => new settings
                                                      # password for AirPlay will be copied

conf.get_service(Protocol.AirPlay).password ="pass"   # Change to something else
settings = await storage.get_settings(conf)           # "conf" exists => return existing settings with
                                                      # AirPlay password set to "pyatv"

# connect will read settings from storage and apply to configuration (e.g. "pyatv" as AirPlay password)
atv = await pyatv.connect(conf, loop, storage=storage)
```

If you make changes to a configuration and want to save them, use
{% include api i="interface.Storage.update_settings" %} explicitly to force an update to storage:

```python
storage = FileStorage("pyatv.conf", loop)
conf = await pyatv.scan(loop, identifier="xxx", storage=storage)[0]  # Scan and insert into storage

conf.get_service(Protocol.AirPlay).credentials ="new_creds"  # Change something in configuration
await storage.update_settings(conf)

# "new_creds" have been saved to storage, so connect till use that password
atv = await pyatv.connect(conf, loop, storage=storage)
```

The recommended way to alter settings is update settings directly in storage, i.e. by changing
the instance returned by {% include api i="interface.Storage.get_settings" %} and not
changing the configuration.

## Using the Storage API

Create a new storage of choice:

```python
from pyatv.storage.file_storage import FileStorage

loop = asyncio.get_event_loop()
storage = FileStorage("pyatv.json", loop)
await storage.load()
```

Note that the storage must be loaded using {% include api i="interface.Storage.load" %} in order to fetch
settings from the underlying storage, e.g. reading from file. Not calling this method results in undefined
behavior.

Scanning with storage:

```python
confs = await pyatv.scan(loop, storage=storage)
```

The storage will automatically be populated with all discovered devices.

To pair with a storage:

```python
pairing = await pair(atvs[0], Protocol.AirPlay, loop, storage=storage)
```

When a successful pairing has been made, the resulting credentials are automatically inserted into
the storage for further references.

To connect with storage:

```python
atv = await pyatv.connect(confs[0], loop, storage=storage)
```

An instance of {% include api i="settings.Settings" %} containing loaded settings is available
via {% include api i="interface.AppleTV.settings" %}.

Changes made to settings in the storage are only stored in memory and must be saved using
{% include api i="interface.Storage.save" %} to make them persistent:

```python
await storage.save()
```

Storages are supposed to keep track of changes and only save changes if something has actually
changed.

### Default File Storage

When using tools bundled with pyatv, e.g. `atvremote` or `atvscript`,
{% include api i="storage/file_storage.FileStorage" %} is used with the file `$HOME/.pyatv.conf`.
You can tap into this storage with your own applications, thus sharing credentials with pyatv.
There is a convenience method called
{% include api i="storage/file_storage.FileStorage.default_storage" %} that is recommended to use
as it is platform agnostic:

```python
loop = asyncio.get_event_loop()
storage = FileStorage.default_storage(loop)
await storage.load()
```
## Changing Settings

As stated in [Storage Guidelines](#storage-guidelines), some settings are only used when connecting
while others can be used at any given time (e.g. port numbers). It is recommended to update settings
prior to connecting, but it is allowed to change setting even after connecting but the changes
might not apply until the next time you connect.

To get settings for a device, use {% include api i="interface.Storage.get_settings" %}:

```python
conf = ... # Scan for device

settings = await storage.get_settings(conf)
```

To change setting, simply set new values according to your needs:

```python
settings.name = "My App"  # Named used when pairing
settings.mac = "aa:bb:cc:dd:ee:ff"  # MAC address pyatv presents itself when needed

settings.raop.password = "never_gonna_give_you_up"
```

Remember to save changes to storage to ensure they are stored persistently
({% include api i="interface.Storage.save" %}).

To find available settings, look at {% include api i="settings.Settings" %} in the API
reference as each field are described there (including default values when applicable).

## Custom Storage Module

To implement your own storage module, it is recommended to inherit from
{% include api i="storage.AbstractStorage" %} and implement the missing methods. Internally `pyatv` uses
[pydantic](https://docs.pydantic.dev/) for the storage model, simplifying things like serialization when
storing and loading settings. The {% include api i="storage.AbstractStorage.storage_model" %} property
is used to get the current representation but also to update it when loading a model from an external
source.

Simply put:

* `save` shall serialize {% include api i="storage.AbstractStorage.storage_model" %} in some way, e.g.
  into JSON or YAML and save that somewhere
* `load` shall take the saved data, de-serialize it and set
  {% include api i="storage.AbstractStorage.storage_model" %} with the de-serialized data

A simple pseudo example looks like this:

```python
import json
from pyatv.storage import AbstractStorage

class CloudStorage(AbstractStorage):

    def __init__(self, cloud_api):
        super().__init__()
        self.cloud_api = cloud_api

    async def save(self) -> None:
        if self.changed:
            json_data = self.storage_model.model_dump_json(exclude_defaults=True)
            await self.cloud_api.save("myfile.json", json_data)
            self.mark_as_saved()

    async def load(self) -> None:
        json_data = await self.cloud_api.load("myfile.json")
        self.storage_model = StorageModel(**json.loads(json_data))
        self.mark_as_saved()

```

Nothing else is really needed to implement a new storage module (implementing `__str__` for debugging
purposes is also recommended). Do note how {% include api i="storage.AbstractStorage.changed" %} and
{% include api i="storage.AbstractStorage.mark_as_saved" %} are used to only save the storage model
in case it was changed. This removes unnecessary writes to disk since the same content would be
re-written every time {% include api i="interface.Storage.save" %} is called otherwise.

More complex implementations may inherit from
{% include api i="interface.Storage" %} directly, but additional care must be taken to implement the
interface correctly.

*Note: Ensure to pass `exclude_defaults=True` when dumping the model, otherwise you will also save
default values. This pollutes the output a lot, but also causes problems if default values are changed
in pyatv as the settings written to storage will be used instead, i.e. old default values.*
