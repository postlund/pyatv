---
layout: template
title: Tutorial
permalink: /documentation/tutorial/
link_group: documentation
---
# :green_book: Table of Contents
{:.no_toc}
* TOC
{:toc}

# Tutorial
Looking at simple example is one thing, building an application is something else. This
tutorial will guide you through building an application that is simple to understand,
but still more complex than the bundled examples. So, grab your favorite beverage and
lets get going! :coffee: :tea:

# The goal: simple web based client
The goal of this tutorial is to build an application that starts a web server and
accepts commands for scanning, connecting to a device, sending remote control commands
and fetching what is currently playing. There might be a bonus at the end, demonstrating
live push updates via websockets if you are lucky... Pairing is left out from the
tutorial as an exercise to you. So you will need to obtain credentials (if
needed) via some other method, e.g. [atvremote](../atvremote#pairing-with-a-device).

Small steps is key, so the tutorial will be divided into the following sections:

1. Basic web server
2. Add scan support
3. Connect to a device
4. Remote control commands
5. Retrieve current play state
6. Closing a connection
7. Some bonuses...

The complete source code will be listed several times along the way. If you're unsure
if you did it right, just scroll down and hopefully you can compare with the expected
result. The final result is [here](#the-complete-example). It is also available as an
example at {% include code file="../examples/tutorial.py" %}.

# Tutorial steps

## 1. Basic web server
Let's get going! First, we're gonna create a web server that will handle the requests
for us. We'll use {% include pypi package="aiohttp" %} for that since it's already a
dependency of pyatv and fairly easy to use. Here's a simple skeleton, save it
as `tutorial.py`:

```python
import asyncio
from aiohttp import web
import pyatv

routes = web.RouteTableDef()

@routes.get('/')
async def scan(request):
    return web.Response(text="Hello world!")

def main():
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app)

if __name__ == "__main__":
    main()
```

Run the script with `python tutorial.py`:

```shell
$ python tutorial.py 
======== Running on http://0.0.0.0:8080 ========
(Press CTRL+C to quit)
```

Open your web browser, navigate to
<a href="http://127.0.0.1:8080">http://127.0.0.1:8080</a> and you should be
greeted by `Hello world!`.

The `scan` method is simply called whenever the index page
is requested (because of `@routes.get('/')`). We'll change the endpoint to `/scan`
in the next section.

## 2. Add scan support
Implementing scanning is rather straight-forward using {% include api i="pyatv.scan" %}.
The tricky part is: what output format should we use? In this example we'll just stick
to a simple human-readble format, but changing to something else like JSON would be
pretty simple as well.

Change the `scan` method into something like this:

```python
@routes.get('/scan')
async def scan(request):
    results = await pyatv.scan(loop=asyncio.get_event_loop())
    output = "\n\n".join(str(result) for result in results)
    return web.Response(text=output)
```

A break-down:
1. First we scan for all devices on the network with {% include api i="pyatv.scan" %},
   passing current event loop as `loop`. This will return a list of
   {% include api i="interface.AppleTV" %} objects.
2. Results are converted into a readable string with two newlines between each device.
3. Content is returned as a text

The output is pretty close to what `atvremote scan` would give. To give an idea of
what it would take to return JSON output instead, here's an example of that (containing
only address and name for each device):

```python
@routes.get('/scan')
async def scan(request):
    devices = []
    for result in await pyatv.scan(loop=asyncio.get_event_loop()):
        devices.append({"name": result.name, "address": str(result.address)})
    return web.json_response(devices)
```

There's an important thing to not here. By default, scanning will take around three
seconds. That means it will take roughly three seconds until the page is rendered.
That might be ok, or it might not be depending on usecase. A potential improvement
is to periodically scan for devices and keep a cache that is immediately returned.
Alternatively, provide another endpoint (e.g. `/trigger_scan`) that performs scanning
in the background and saves the result. Then `/scan` can return that result.

*Tip: {% include code file="scripts/atvscript.py" %} is a good reference if you
need help with converting output to JSON.*

## 3. Connect to a device
Now we can find devices, next step is to connect to one. We'll support doing that
by ID. We will also support passing in credentials. A typical call to connect will
look like this:

```raw
http://127.0.0.1:8080/connect/aabbccddee?mrp=1234&dmap=5678
```

The ID in this case is `aabbccddee` and credentials are passed to MRP as 1234
and 5678 for DMAP. Argument names for credentials will be the same as in
{% include api i="const.Protocol" %} but converted to lower-case.

Let's ignore credentials for now though, focusing on just connecting to the device:

```python
@routes.get('/connect/{id}')
async def connect(request):
    loop = asyncio.get_event_loop()
    device_id = request.match_info["id"]

    results = await pyatv.scan(identifier=device_id, loop=loop)
    if not results:
        return web.Response(text="Device not found", status=500)

    try:
        atv = await pyatv.connect(results[0], loop=loop)
    except Exception as ex:
        return web.Response(text=f"Failed to connect to device: {ex}", status=500)

    return web.Response(text=f"Connected to device {device_id}")
```

So, there's a bunch of code here:

1. There's built-in support for matchers in {% include pypi package="aiohttp" %},
   so the `<id>` is easily extracted with `request.match_info["id"]`.
2. Next, scan for device with the requested device id by passing it via
   `identifier`. If no device is not found, return an error message and error code.
3. Try to connect, making sure that we catch any error and return another error
   message in case connect failed.
4. At the end, return a message stating we are connected.

Assuming everything went OK, we have a handle to our device via `atv`. We need
to save that somewhere (and make sure we close the connection properly when
exiting the script), since we need it in other request handlers.

The `web.Application` instance can store global variables for us, so lets use
that. Before returning in `connect`, make this change:

```python
    ...
    except Exception as ex:
        return web.Response(text=f"Failed to connect to device: {ex}", status=500)

    request.app["atv"][device_id] = atv  # <-- Add this
    return web.Response(text=f"Connected to device {device_id}")
```

We can then access our device from other handlers via `request.app[<id>]` later.
But we should also close it when exiting the script. We can do that by modifying
the startup code like this:

```python
async def on_shutdown(app: web.Application) -> None:
    for atv in app["atv"].values():
        atv.close()

def main():
    app = web.Application()
    app["atv"] = {}
    app.add_routes(routes)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app)

...
```

The `on_shutdown` method will be called when the script is exited, e.g. by
pressing Ctrl+C. There's one more guard we should add, making sure we don't try
to connect if we are already connected. A simple check at the top will fix that:

```python
@routes.get('/connect/{id}')
async def connect(request):
    loop = asyncio.get_event_loop()
    device_id = request.match_info["id"]
    if device_id in request.app["atv"]:
        return web.Response(text=f"Already connected to {device_id}")
```


Next part is to add parsing of credentials. We'll create a
helper method for that, which will iterate all services and look for credentials
in the GET-parameters:

```python
def add_credentials(config, query):
    for service in config.services:
        proto_name = service.protocol.name.lower()  # E.g. Protocol.MRP -> "mrp"
        if proto_name in query:
            config.set_credentials(service.protocol, query[proto_name])
```

Here, `query` is a map with all values passed via the URL, e.g.
`xxx?mrp=1234&dmap=5678` => `{"mrp": "1234", "dmap": "5678"}`. Add `add_credentials`
above the `scan` method and call it before connecting:

```python
    ...
    if not results:
        return web.Response(text="Device not found", status=500)

    add_credentials(results[0], request.query)

    try:
        atv = await pyatv.connect(results[0], loop=loop)
    ...
```

For the sake of completeness, here is the final script:

<details>

```python
import asyncio
from aiohttp import web
import pyatv

routes = web.RouteTableDef()


def add_credentials(config, query):
    for service in config.services:
        proto_name = service.protocol.name.lower()
        if proto_name in query:
            config.set_credentials(service.protocol, query[proto_name])


@routes.get("/scan")
async def scan(request):
    results = await pyatv.scan(loop=asyncio.get_event_loop())
    output = "\n\n".join(str(result) for result in results)
    return web.Response(text=output)


@routes.get("/connect/{id}")
async def connect(request):
    loop = asyncio.get_event_loop()
    device_id = request.match_info["id"]
    if device_id in request.app["atv"]:
        return web.Response(text=f"Already connected to {device_id}")

    results = await pyatv.scan(identifier=device_id, loop=loop)
    if not results:
        return web.Response(text="Device not found", status=500)

    add_credentials(results[0], request.query)

    try:
        atv = await pyatv.connect(results[0], loop=loop)
    except Exception as ex:
        return web.Response(text=f"Failed to connect to device: {ex}", status=500)

    request.app["atv"][device_id] = atv
    return web.Response(text=f"Connected to device {device_id}")


async def on_shutdown(app: web.Application) -> None:
    for atv in app["atv"].values():
        atv.close()


def main():
    app = web.Application()
    app["atv"] = {}
    app.add_routes(routes)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app)


if __name__ == "__main__":
    main()
```

</details>

## 4. Remote control commands

Nice, we are connected! Now, continue with remote control commands. We'll
stick with single tap actions for now. If you want support for other actions, e.g.
double tap, pass the action as an argument and access it via `request.query`.

Here's a basic handler for the remote control:

```python
@routes.get("/remote_control/{id}/{command}")
async def remote_control(request):
    device_id = request.match_info["id"]
    atv = request.app["atv"][device_id]

    try:
        await getattr(atv.remote_control, request.match_info["command"])()
    except Exception as ex:
        return web.Response(text=f"Remote control command failed: {ex}")

    return web.Response(text="OK")
```

By using `getattr`, we can look up commands dynamically without having to
write them in code. Use the same names as methods
in {% include api i="interface.RemoteControl" %}. We should do one more thing:
check that we are connected, e.g. like this:

```python
@routes.get("/remote_control/{id}/{command}")
async def remote_control(request):
    device_id = request.match_info["id"]
    atv = request.app["atv"].get(device_id)
    if not atv:
        return web.Response(text=f"Not connected to {device_id}", status=500)

    ...
```

To trigger a command, use a URL like this:

```raw
http://127.0.0.1:8080/remote_control/aabbccddee/menu
```

You might have noticed that the device id is passed here as well. By doing that,
multiple devices can be controlled at the same time. Pretty cool, huh?

## 4.5. Some refactoring

This is a pattern we will see a lot:

```python
@routes.get("/something/{id}/{command}")
async def something(request):
    device_id = request.match_info["id"]
    atv = request.app["atv"].get(device_id)
    if not atv:
        return web.Response(text=f"Not connected to {device_id}", status=500)

    ...
```

To reduce code, we can create a decorator taking care of this for us. Here's
one way:

```python
def web_command(method):
    async def _handler(request):
        device_id = request.match_info["id"]
        atv = request.app["atv"].get(device_id)
        if not atv:
            return web.Response(text=f"Not connected to {device_id}", status=500)
        return await method(request, atv)
    return _handler
```

This decorator will verify that a device handler exists for the given id, returning
an error otherwise. It will also pass the device handler (`atv`) as a second
argument to the handler method so it is conveniently available. Re-writing original
`remote_control` method using the decorator, it will now look like this:

```python
@routes.get("/remote_control/{id}/{command}")
@web_command
async def remote_control(request, atv):
    try:
        await getattr(atv.remote_control, request.match_info["command"])()
    except Exception as ex:
        return web.Response(text=f"Remote control command failed: {ex}")
    return web.Response(text="OK")
```

Again, for completeness, here is the code so far:

<details>

```python
import asyncio
from aiohttp import web
import pyatv


routes = web.RouteTableDef()


def web_command(method):
    async def _handler(request):
        device_id = request.match_info["id"]
        atv = request.app["atv"].get(device_id)
        if not atv:
            return web.Response(text=f"Not connected to {device_id}", status=500)
        return await method(request, atv)
    return _handler


def add_credentials(config, query):
    for service in config.services:
        proto_name = service.protocol.name.lower()
        if proto_name in query:
            config.set_credentials(service.protocol, query[proto_name])


@routes.get("/scan")
async def scan(request):
    results = await pyatv.scan(loop=asyncio.get_event_loop())
    output = "\n\n".join(str(result) for result in results)
    return web.Response(text=output)


@routes.get("/connect/{id}")
async def connect(request):
    loop = asyncio.get_event_loop()
    device_id = request.match_info["id"]
    if device_id in request.app["atv"]:
        return web.Response(text=f"Already connected to {device_id}")

    results = await pyatv.scan(identifier=device_id, loop=loop)
    if not results:
        return web.Response(text="Device not found", status=500)

    add_credentials(results[0], request.query)

    try:
        atv = await pyatv.connect(results[0], loop=loop)
    except Exception as ex:
        return web.Response(text=f"Failed to connect to device: {ex}", status=500)

    request.app["atv"][device_id] = atv
    return web.Response(text=f"Connected to device {device_id}")


@routes.get("/remote_control/{id}/{command}")
@web_command
async def remote_control(request, atv):
    try:
        await getattr(atv.remote_control, request.match_info["command"])()
    except Exception as ex:
        return web.Response(text=f"Remote control command failed: {ex}")
    return web.Response(text="OK")


async def on_shutdown(app: web.Application) -> None:
    for atv in app["atv"].values():
        atv.close()


def main():
    app = web.Application()
    app["atv"] = {}
    app.add_routes(routes)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app)


if __name__ == "__main__":
    main()
```

</details>

## 5. Retrieve current play state

With the new decorator, exposing play status is a breeze:

```python
@routes.get("/playing/{id}")
@web_command
async def playing(request, atv):
    try:
        status = await atv.metadata.playing()
    except Exception as ex:
        return web.Response(text=f"Remote control command failed: {ex}")
    return web.Response(text=str(status))
```

Current play status is retrieved via {% include api i="interface.Metadata.playing" %},
converted to a string and returned.

## 6. Closing a connection

It might be convenient to have a function that can close a connection, so lets
add that:

```python
@routes.get("/close/{id}")
@web_command
async def close_connection(request, atv):
    atv.close()
    request.app["atv"].pop(request.match_info["id"])
    return web.Response(text="OK")
```

We basically just call close on the device handler and remove our internally
stored reference. This will allow us to re-connect again when needed.

*Note: No error handling here if device is not connected.*

## 7. Bonus: Handle device disconnects

There's currently a problem: if the connection for some reason is lost, the
device handler will still be in `request.app["pyatv"]` (looking like
it is connected) allowing new commands to be issued. These will obviously fail
however and it will not be possible to call connect again until close has
been called. It would be nice to clean up the handler in case the connection is
lost, so connect can be called directly.

We can do this by setting up a listener for device updates, just removing the
handler when the connection is lost. We start by declaring a device listener,
which is an implementation of {% include api i="interface.DeviceListener" %}:

```python
class DeviceListener(pyatv.interface.DeviceListener):
    def __init__(self, app, identifier):
        self.app = app
        self.identifier = identifier

    def connection_lost(self, exception: Exception) -> None:
        self._remove()

    def connection_closed(self) -> None:
        self._remove()

    def _remove(self):
        self.app["atv"].pop(self.identifier)
        self.app["listeners"].remove(self)
```

It will keep track of `app` and the device identifier as we will create one
listener per device. When a connection is either lost (unknown reason) or
intentionally closed (e.g. via the close command), remove the handler and
current listener from internal list. More on `"listeners"` next.

So, we need to make a few adjustments. First and foremost, we need somewhere
to store the listener objects. It's very tempting to do somethinglike this:

```python
atv.listener = DeviceListener(request.app, device_id)
```

The problem however is that pyatv uses *weak references* to listener objects.
In practice, that means as soon as the variable holding a reference to the
object goes out of scope, the object (i.e. the `DeviceListener` instance) will
be taken care of by the garbage collector. Unless someone else has a reference
to it of course. We are gonna put listeners in a list and remove them once a
connection is lost. That's what the last line in `DeviceListener` does for us.
This way there will be a reference to the listener instance and we don't risk
it getting garbage collected. Add the list in the setup code:

```python
...
def main():
    app = web.Application()
    app["atv"] = {}
    app["listeners"] = []  # <-- add this
    app.add_routes(routes)
    ...
```

Now we need to create the actual listener, make sure it receives updates and
also add it to the `listeners` list (in the `connect` method):

```python
    ...
    except Exception as ex:
        return web.Response(text=f"Failed to connect to device: {ex}", status=500)

    listener = DeviceListener(request.app, device_id)
    atv.listener = listener
    request.app["listeners"].append(listener)

    request.app["atv"][device_id] = atv
    ...
```

You can read more about device listeners [here](../../development/listeners/#device-updates),
if you want some additional context.

There's one more thing to do: get rid of the line that removes the device handler
in the close command:

```python
@routes.get("/close/{id}")
@web_command
async def close_connection(request, atv):
    atv.close()
    return web.Response(text="OK")
```

Calling `atv.close()` will trigger `connection_closed` in the device listener,
which in turn will remove the device handler and pop the listener for us.

## 8. Bonus: Push updates

If you made it this far: good job! Adding support for live push updates is a bit
tricky, but not that hard. There are three steps to this:

1. Add a websocket request handler where clients can subscribe to updates
2. Create and set up a {% include api i="interface.PushListener" %} that
   receives updates and forward them over websockets
3. Serve a small web page with some javascript that connects to the websocket
   endpoint and updates an element when status change

Let's take it one step at the time.

### Websocket request handler

A websocket request handler works similarly to other request handlers (e.g. GET),
but since a websocket is generally open over longer period of time, it doesn't
return until the client disconnects. We will not be handling any commands from
the client, just let the connection remain open and save a handler to it internally,
so the push listener can send updates later. We'll start by adding somewhere to
store these handlers (in the setup code):

```python
def main():
    app = web.Application()
    app["atv"] = {}
    app["listeners"] = []
    app["clients"] = {}  # <--- add this
    ...
```

We will map the device id to a list of clients, so that multiple clients can
connect and receive updates concurrently (that's why a dict is used). Now,
let's define the websocket handler:

```python
@routes.get("/ws/{id}")
@web_command
async def websocket_handler(request, atv):
    device_id = request.match_info["id"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app["clients"].setdefault(device_id, []).append(ws)

    playstatus = await atv.metadata.playing()
    await ws.send_str(str(playstatus))

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            # Handle custom commands from client here
            if msg.data == "close":
                await ws.close()
        elif msg.type == WSMsgType.ERROR:
            print(f"Connection closed with exception: {ws.exception()}")

    request.app["clients"][device_id].remove(ws)

    return ws
```

Some code is new, some we have already seen and some is boiler plate. A break-down:

1. Endpoint `/ws/{id}` is used to map which device to receive updates from.
2. `ws` is the "response" we use to send and receive messages (this is straight
   from the [aiohttp documentation](https://docs.aiohttp.org/en/stable/web_quickstart.html#websockets)).
   Notice that this handler is saved in `app["clients"]` that we previously added.
3. When a new client connects, we want to send an initial update with what is
   currently playing. So current state is fetched, converted to a string and sent.
4. Loop (from documentation) waiting for incoming data. We don't do much here,
   but an example handling a `close` command from the client is left for inspiration.
5. When the connection is closed, remove the handle so we don't try to send updates
   on a closed connection later.

Make sure to import `WSMsgType` at the top as well:

```python
from aiohttp import WSMsgType, web
```

That's it for the websocket handler. You can add additional websocket commands
if you like in the loop, but it's not used here.

### Handling push updates

At this stage, websocket clients can connect and we store handlers to them in
`app["clients"][<id>]` per device. Now we need to subscribe to push updates from
the device and forward them to all websocket connections for a particular
device. The natural way would be to add a new class, implement
{% include api i="interface.PushListener" %} and add logic there. An easier way
however, is to use the fact that we have a device listener already. We can just
implement the relevant methods there and use that as a push listener as well.
By doing so, we don't have to handle a new listener (weak reference problem exists
here as well) and it requires a bit less code.

Start by inheriting from {% include api i="interface.PushListener" %}:

```python
class DeviceListener(pyatv.interface.DeviceListener, pyatv.interface.PushListener):
```

Now, add these methods to `DeviceListener`:

```python
    def playstatus_update(self, updater, playstatus: pyatv.interface.Playing) -> None:
        clients = self.app["clients"].get(self.identifier, [])
        for client in clients:
            asyncio.ensure_future(client.send_str(str(playstatus)))

    def playstatus_error(self, updater, exception: Exception) -> None:
        pass
```

When an update is received in `playstatus_update`, look up all client handlers for
the device and send a string version of it. Note that `send_str` is a coroutine and
`playstatus_update` is a plain callback function, so `asyncio.ensure_future` is
used to schedule a call on the event loop. We ignore any error updates for now by
leaving that method empty.

The final piece is to subscribe to push updates, so our new methods are actually
called at all. We do this in `connect`:

```python
    ...
    listener = DeviceListener(request.app, device_id)
    atv.listener = listener
    atv.push_updater.listener = listener  # <-- set the listener
    atv.push_updater.start()              # <-- start subscribing to updates
    request.app["listeners"].append(listener)
    ...
```

We are basically done with the websocket implementation now and you can try it out
with a third-part client if you like. But it's convenient if we provide a simple
web page that updates for us. So let's finalize the script with that.

### Websocket client page
This can't be stressed enough: the solution implemented here is *not* a good
solution. It is only meant to be simple, keeping everything in the same file.
Preferably the client page would be stored as a separate file and served as a
static file. We will however bundle a basic page in the script, so add this at the
top (below the imports):

```python
PAGE = """
<script>
let socket = new WebSocket('ws://' + location.host + '/ws/DEVICE_ID');

socket.onopen = function(e) {
  document.getElementById('status').innerText = 'Connected!';
};

socket.onmessage = function(event) {
  document.getElementById('state').innerText = event.data;
};

socket.onclose = function(event) {
  if (event.wasClean) {
    document.getElementById('status').innerText = 'Connection closed cleanly!';
  } else {
    document.getElementById('status').innerText = 'Disconnected due to error!';
  }
  document.getElementById('state').innerText = "";
};

socket.onerror = function(error) {
  document.getElementById('status').innerText = 'Failed to connect!';
};
</script>
<div id="status">Connecting...</div>
<div id="state"></div>
"""
```

This page has two `<div>` elements: one for connection status and one for play state.
A websocket connection is set up, connecting to `ws://<server address>/ws/DEVICE_ID`
(we will replace `DEVICE_ID` with the correct id). The various callback
functions then just update what's shown in the div elements.

Now we need a handler to serve the page. Here's what that looks like:

```python
@routes.get("/state/{id}")
async def state(request):
    return web.Response(
        text=PAGE.replace("DEVICE_ID", request.match_info["id"]),
        content_type="text/html",
    )
```

The `PAGE` is just returned, but `DEVICE_ID` is replaced with the correct id.

To test this out, start by opening

```raw
http://127.0.0.1:8080/connect/aabbccddee
```

Once connected, navigate to:

```raw
http://127.0.0.1:8080/state/aabbccddee
```

You should hopefully see the current state immediately. If you start playing
something on the device, it should hopefully update instantaneously!

# The complete example

Here is the final code for the application (or here:
{% include code file="../examples/tutorial.py" %}):

<details>

```python
import asyncio
from aiohttp import WSMsgType, web
import pyatv

PAGE = """
<script>
let socket = new WebSocket('ws://' + location.host + '/ws/DEVICE_ID');

socket.onopen = function(e) {
  document.getElementById('status').innerText = 'Connected!';
};

socket.onmessage = function(event) {
  document.getElementById('state').innerText = event.data;
};

socket.onclose = function(event) {
  if (event.wasClean) {
    document.getElementById('status').innerText = 'Connection closed cleanly!';
  } else {
    document.getElementById('status').innerText = 'Disconnected due to error!';
  }
  document.getElementById('state').innerText = "";
};

socket.onerror = function(error) {
  document.getElementById('status').innerText = 'Failed to connect!';
};
</script>
<div id="status">Connecting...</div>
<div id="state"></div>
"""

routes = web.RouteTableDef()


class DeviceListener(pyatv.interface.DeviceListener, pyatv.interface.PushListener):
    def __init__(self, app, identifier):
        self.app = app
        self.identifier = identifier

    def connection_lost(self, exception: Exception) -> None:
        self._remove()

    def connection_closed(self) -> None:
        self._remove()

    def _remove(self):
        self.app["atv"].pop(self.identifier)
        self.app["listeners"].remove(self)

    def playstatus_update(self, updater, playstatus: pyatv.interface.Playing) -> None:
        clients = self.app["clients"].get(self.identifier, [])
        for client in clients:
            asyncio.ensure_future(client.send_str(str(playstatus)))

    def playstatus_error(self, updater, exception: Exception) -> None:
        pass


def web_command(method):
    async def _handler(request):
        device_id = request.match_info["id"]
        atv = request.app["atv"].get(device_id)
        if not atv:
            return web.Response(text=f"Not connected to {device_id}", status=500)
        return await method(request, atv)

    return _handler


def add_credentials(config, query):
    for service in config.services:
        proto_name = service.protocol.name.lower()
        if proto_name in query:
            config.set_credentials(service.protocol, query[proto_name])


@routes.get("/state/{id}")
async def state(request):
    return web.Response(
        text=PAGE.replace("DEVICE_ID", request.match_info["id"]),
        content_type="text/html",
    )


@routes.get("/scan")
async def scan(request):
    results = await pyatv.scan(loop=asyncio.get_event_loop())
    output = "\n\n".join(str(result) for result in results)
    return web.Response(text=output)


@routes.get("/connect/{id}")
async def connect(request):
    loop = asyncio.get_event_loop()
    device_id = request.match_info["id"]
    if device_id in request.app["atv"]:
        return web.Response(text=f"Already connected to {device_id}")

    results = await pyatv.scan(identifier=device_id, loop=loop)
    if not results:
        return web.Response(text="Device not found", status=500)

    add_credentials(results[0], request.query)

    try:
        atv = await pyatv.connect(results[0], loop=loop)
    except Exception as ex:
        return web.Response(text=f"Failed to connect to device: {ex}", status=500)

    listener = DeviceListener(request.app, device_id)
    atv.listener = listener
    atv.push_updater.listener = listener
    atv.push_updater.start()
    request.app["listeners"].append(listener)

    request.app["atv"][device_id] = atv
    return web.Response(text=f"Connected to device {device_id}")


@routes.get("/remote_control/{id}/{command}")
@web_command
async def remote_control(request, atv):
    try:
        await getattr(atv.remote_control, request.match_info["command"])()
    except Exception as ex:
        return web.Response(text=f"Remote control command failed: {ex}")
    return web.Response(text="OK")


@routes.get("/playing/{id}")
@web_command
async def playing(request, atv):
    try:
        status = await atv.metadata.playing()
    except Exception as ex:
        return web.Response(text=f"Remote control command failed: {ex}")
    return web.Response(text=str(status))


@routes.get("/close/{id}")
@web_command
async def close_connection(request, atv):
    atv.close()
    return web.Response(text="OK")


@routes.get("/ws/{id}")
@web_command
async def websocket_handler(request, pyatv):
    device_id = request.match_info["id"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app["clients"].setdefault(device_id, []).append(ws)

    playstatus = await pyatv.metadata.playing()
    await ws.send_str(str(playstatus))

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            # Handle custom commands from client here
            if msg.data == "close":
                await ws.close()
        elif msg.type == WSMsgType.ERROR:
            print(f"Connection closed with exception: {ws.exception()}")

    request.app["clients"][device_id].remove(ws)

    return ws


async def on_shutdown(app: web.Application) -> None:
    for atv in app["atv"].values():
        atv.close()


def main():
    app = web.Application()
    app["atv"] = {}
    app["listeners"] = []
    app["clients"] = {}
    app.add_routes(routes)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app)


if __name__ == "__main__":
    main()
```

</details>

# Some final notes
This is the end of the tutorial, have some :cake:! Feel free to use this code
in any way you like (there's no copyright attached to it), but remember that
it's more for inspiration than complete project. There are pitfalls,
especially with regards to error handling.

If you want some inspiration for additional things to do, here are few:

* Implement additional commands, e.g. volume control, app launching, artwork
  or streaming
* Support commands over websocket instead of GET requests
* Serve interface via static files (and improve it!)
* Implement pairing support
* Allow triggering of a scan and return results via websocket
* Add a command showing all connected devices
* Create a container class, eliminating the need for three variables in `app`
* Combine `web_command` and `routes.get` into a single decorator, e.g.
  `@web_command("/ws/{id}")`
* Allow some way to enable debugging, either via CLI flags, a new endpoint
  or websockets
* Do all of the above and build a simple remote control!

Regarding websockets... currently only the play state is sent over websockets.
Some means of multiplexing needs to be added to support additional commands,
e.g. by sending JSON (a dict) instead.
