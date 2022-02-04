"""Simple json api client implemented in pyatv"""

import os
import datetime
import traceback
from enum import Enum
from ipaddress import ip_address

import logging
import asyncio
from aiohttp import WSMsgType, web

import pyatv
from pyatv.interface import (
    App,
    Apps,
    Audio,
    DeviceListener,
    Playing,
    Power,
    PowerListener,
    PushListener,
    RemoteControl,
    Stream,
    retrieve_commands,
)


DEVICES = """
<script>
setTimeout(function(){
   window.location.reload(1);
}, 5 * 1000);
</script>
<div id="devices">DEVICES</div>
"""


STATE = """
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


class PushPrinter(DeviceListener, PushListener, PowerListener):
    """Listener for device and push updates events."""

    def __init__(self, app, identifier):
        """Initialize a new PushPrinter."""
        self.app = app
        self.identifier = identifier

    def connection_lost(self, exception: Exception) -> None:
        """Call when connection was lost."""
        self._remove()

    def connection_closed(self) -> None:
        """Call when connection was closed."""
        self._remove()

    def _remove(self):
        self.app["atv"].pop(self.identifier)
        self.app["listeners"].remove(self)

    def playstatus_update(self, updater, playstatus: Playing) -> None:
        """Call when play status was updated."""
        clients = self.app["clients"].get(self.identifier, [])
        atv = self.app["atv"][self.identifier]
        for client in clients:
            asyncio.ensure_future(
                client.send_json(
                    output_playing(playstatus, atv.metadata.app)
                )
            )

    def playstatus_error(self, updater, exception: Exception) -> None:
        """Call when an error occurred."""

    def powerstate_update(self, old_state, new_state):
        """Call when power state was updated."""
        clients = self.app["clients"].get(self.identifier, [])
        for client in clients:
            asyncio.ensure_future(
                client.send_json(
                    output(
                        True,
                        values={"power_state": new_state.name.lower()},
                    )
                )
            )


def output(success: bool, error=None, exception=None, values=None):
    """Produce output in intermediate format before conversion"""
    now = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    result = {"result": "success" if success else "failure", "datetime": str(now)}
    if error:
        result["error"] = error
    if exception:
        result["exception"] = str(exception)
        result["stacktrace"] = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
    if values:
        result.update(**values)
    return result


def output_playing(playing: Playing, app: App):
    """Produce output for what is currently playing."""

    def _convert(field):
        if isinstance(field, Enum):
            return field.name.lower()
        return field if field else None

    commands = retrieve_commands(Playing)
    values = {k: _convert(getattr(playing, k)) for k in commands}
    if app:
        values["app"] = app.name
        values["app_id"] = app.identifier
    else:
        values["app"] = None
        values["app_id"] = None
    return output(True, values=values)


def web_command(method):
    """Decorate a web request handler."""

    async def _handler(request):
        device_id = request.match_info["id"]
        atv = request.app["atv"].get(device_id)
        if not atv:
            return web.json_response(
                output(False, error=f"Not connected to {device_id}")
            )
        return await method(request, atv)

    return _handler


def add_credentials(config, query):
    """Add credentials to pyatv device configuration."""
    for service in config.services:
        proto_name = service.protocol.name.lower()
        if proto_name in query:
            config.set_credentials(service.protocol, query.get(proto_name))

    for service in config.services:
        if service.credentials:
          return True

    return False


routes = web.RouteTableDef()


@routes.get("/version")
async def version(request):
    """Handle request to receive version pyatv."""
    return web.json_response(
        output(True, values={"version": pyatv.const.__version__})
    )


@routes.get("/devices")
async def devices(request):
    """List devices connect."""
    devices = []
    for device in request.app["atv"]:
        devices.append(
            f"<a href='/state/{device}' target='_blank'>{device}</a>"
        )
    if devices:
        devices = str("</br>".join(devices))
    else:
        devices = str("Empty devices list")
    return web.Response(
        text=DEVICES.replace("DEVICES", devices),
        content_type="text/html",
    )


@routes.get("/state/{id}")
async def state(request):
    """Handle request to receive push updates."""
    return web.Response(
        text=STATE.replace("DEVICE_ID", request.match_info["id"]),
        content_type="text/html",
    )


@routes.get("/scan/")
async def scan(request):
    """Handle request to scan for devices."""

    def _convert(hosts):
        if hosts:
            ip_split = hosts.split(",")
            return [ip_address(ip) for ip in ip_split]
        return None

    hosts = _convert(request.query.get("hosts"))
    atvs = []
    for atv in await pyatv.scan(loop=asyncio.get_event_loop(), hosts=hosts):
        services = []
        for service in atv.services:
            services.append(
                {"protocol": service.protocol.name.lower(), "port": service.port}
            )
        atvs.append(
            {
                "name": atv.name,
                "address": str(atv.address),
                "identifier": atv.identifier,
                "services": services,
            }
        )
    return web.json_response(output(True, values={"devices": atvs}))

@routes.get("/connect/{id}")
async def connect(request):
    """Handle request to connect to a device."""
    loop = asyncio.get_event_loop()
    device_id = request.match_info["id"]
    if device_id in request.app["atv"]:
        return web.json_response(
            output(True, values={"connection": "connected"})
        )

    options = {}
    if ip_address(device_id):
        options["hosts"] = [device_id]
    else:
        options["identifier"] = device_id
    results = await pyatv.scan(loop=loop, **options)
    if not results:
        return web.json_response(output(False, error="Device not found"))

    if not add_credentials(results[0], request.query):
      return web.json_response(
          output(False, error="Failed to connect to device, empty Credentials")
      )

    try:
        atv = await pyatv.connect(results[0], loop=loop)
    except Exception as ex:
        return web.json_response(
            output(False, error="Failed to connect to device", exception=ex)
        )

    push_listener  = PushPrinter(request.app, device_id)

    atv.power.listener = push_listener
    atv.listener = push_listener
    atv.push_updater.listener = push_listener
    atv.push_updater.start()
    request.app["listeners"].append(push_listener)

    request.app["atv"][device_id] = atv
    return web.json_response(output(True, values={"connection": "connected"}))


@routes.get("/command/{id}/{command}")
@web_command
async def command(request, atv):
    """Handle remote command request."""
    ctrl = retrieve_commands(RemoteControl)
    power = retrieve_commands(Power)
    stream = retrieve_commands(Stream)
    apps = retrieve_commands(Apps)
    audio = retrieve_commands(Audio)

    command = request.match_info["command"]

    try:
        if command in audio:
            await getattr(atv.audio, command)()
        if command in ctrl:
            await getattr(atv.remote_control, command)()
        if command in power:
            await getattr(atv.power, command)()
        if command in stream:
            await getattr(atv.stream, command)()
        if command in apps:
            await getattr(atv.apps, command)()
    except Exception as ex:
        return web.json_response(
            output(False, error="Remote control command failed", exception=ex)
        )
    return web.json_response(output(True, values={"command": command}))


@routes.get("/playing/{id}")
@web_command
async def playing(request, atv):
    """Handle request for current play status."""
    try:
        playstatus = await atv.metadata.playing()
    except Exception as ex:
        return web.json_response(
            output(False, error="Remote control command failed", exception=ex)
        )
    return web.json_response(output_playing(playstatus, atv.metadata.app))


@routes.get("/close/{id}")
@web_command
async def close_connection(request, atv):
    """Handle request to close a connection."""
    atv.close()
    return web.json_response(output(True, values={"connection": "closed"}))


@routes.get("/ws/{id}")
@web_command
async def websocket_handler(request, atv):
    """Handle incoming websocket requests."""
    device_id = request.match_info["id"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app["clients"].setdefault(device_id, []).append(ws)

    playstatus = await atv.metadata.playing()
    await ws.send_json(output_playing(playstatus, atv.metadata.app))

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
    """Call when application is shutting down."""
    for atv in app["atv"].values():
        atv.close()


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", 8080)

    access_log = logging.getLogger('aiohttp.access')
    access_log.setLevel(logging.INFO)
    access_log.addHandler(logging.StreamHandler())
    access_log_format = '%a %t "%r" %s %b "%{User-Agent}i" %Tfsec'

    app = web.Application()
    app["atv"] = {}
    app["listeners"] = []
    app["clients"] = {}

    app.add_routes(routes)
    app.on_shutdown.append(on_shutdown)
    web.run_app(
        app, host=host, port=port,
        access_log=access_log,
        access_log_format=access_log_format
    )


if __name__ == "__main__":
    main()