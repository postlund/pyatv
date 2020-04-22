#!/usr/bin/env python3
"""Tool modelled to be used for scripting."""

import sys
import json
import asyncio
import logging
import argparse
import datetime
import traceback
from enum import Enum

from pyatv import connect, const, scan
from pyatv.const import Protocol
from pyatv.interface import (
    App,
    Playing,
    RemoteControl,
    PushListener,
    PowerListener,
    DeviceListener,
    retrieve_commands,
)
from pyatv.scripts import TransformProtocol, VerifyScanHosts, TransformOutput

_LOGGER = logging.getLogger(__name__)


class PushPrinter(PushListener):
    """Listen for push updates and print changes."""

    def __init__(self, formatter, atv):
        """Initialize a new PushPrinter."""
        self.formatter = formatter
        self.atv = atv

    def playstatus_update(self, updater, playstatus: Playing) -> None:
        """Inform about changes to what is currently playing."""
        print(
            self.formatter(output_playing(playstatus, self.atv.metadata.app)),
            flush=True,
        )

    def playstatus_error(self, updater, exception: Exception) -> None:
        """Inform about an error when updating play status."""
        print(self.formatter(output(False, exception=exception)), flush=True)


class PowerPrinter(PowerListener):
    """Listen for power updates and print changes."""

    def __init__(self, formatter):
        """Initialize a new PowerPrinter."""
        self.formatter = formatter

    def powerstate_update(
        self, old_state: const.PowerState, new_state: const.PowerState
    ):
        """Device power state was updated."""
        print(
            self.formatter(
                output(True, values={"power_state": new_state.name.lower()})
            ),
            flush=True,
        )


class DevicePrinter(DeviceListener):
    """Listen for generic device updates and print them."""

    def __init__(self, formatter, abort_sem):
        """Initialize a new DeviceListener."""
        self.formatter = formatter
        self.abort_sem = abort_sem

    def connection_lost(self, exception):
        """Call when unexpectedly being disconnected from device."""
        print(
            self.formatter(
                output(False, exception=exception, values={"connection": "lost"})
            ),
            flush=True,
        )
        self.abort_sem.release()

    def connection_closed(self):
        """Call when connection was (intentionally) closed."""
        print(self.formatter(output(True, values={"connection": "closed"})), flush=True)
        self.abort_sem.release()


async def wait_for_input(loop, abort_sem):
    """Wait for user input (enter) or abort signal."""
    reader = asyncio.StreamReader(loop=loop)
    reader_protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)
    await asyncio.wait(
        [reader.readline(), abort_sem.acquire()], return_when=asyncio.FIRST_COMPLETED
    )


def output(success: bool, error=None, exception=None, values=None):
    """Produce output in intermediate format before conversion."""
    now = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    output = {"result": "success" if success else "failure", "datetime": str(now)}
    if error:
        output["error"] = error
    if exception:
        output["exception"] = str(exception)
        output["stacktrace"] = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
    if values:
        output.update(**values)
    return output


def output_playing(playing: Playing, app: App):
    """Produce output for what is currently playing."""

    def _convert(field):
        if isinstance(field, Enum):
            return field.name.lower()
        return field if field else None

    commands = retrieve_commands(Playing)
    values = {k: _convert(getattr(playing, k)) for k in commands.keys()}
    if app:
        values["app"] = app.name
        values["app_id"] = app.identifier
    else:
        values["app"] = None
        values["app_id"] = None
    return output(True, values=values)


async def _scan_devices(loop, hosts):
    atvs = []
    for atv in await scan(loop, hosts=hosts):
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
    return output(True, values={"devices": atvs})


async def _autodiscover_device(args, loop):
    options = {"identifier": args.id, "protocol": args.protocol}

    if args.scan_hosts:
        options["hosts"] = args.scan_hosts

    atvs = await scan(loop, **options)

    if not atvs:
        return None

    apple_tv = atvs[0]

    def _set_credentials(protocol, field):
        service = apple_tv.get_service(protocol)
        if service:
            value = service.credentials or getattr(args, field)
            service.credentials = value

    _set_credentials(Protocol.DMAP, "dmap_credentials")
    _set_credentials(Protocol.MRP, "mrp_credentials")
    _set_credentials(Protocol.AirPlay, "airplay_credentials")

    return apple_tv


async def _handle_command(args, abort_sem, loop):
    if args.command == "scan":
        return await _scan_devices(loop, args.scan_hosts)

    config = await _autodiscover_device(args, loop)
    if not config:
        return output(False, "device_not_found")

    atv = await connect(config, loop, protocol=Protocol.MRP)
    try:
        return await _run_command(atv, args, abort_sem, loop)
    finally:
        atv.close()


async def _run_command(atv, args, abort_sem, loop):
    if args.command == "playing":
        return output_playing(await atv.metadata.playing(), atv.metadata.app)

    if args.command == "push_updates":
        power_listener = PowerPrinter(args.output)
        device_listener = DevicePrinter(args.output, abort_sem)
        push_listener = PushPrinter(args.output, atv)

        atv.power.listener = power_listener
        atv.listener = device_listener
        atv.push_updater.listener = push_listener
        atv.push_updater.start()
        print(
            args.output(
                output(True, values={"power_state": atv.power.power_state.name.lower()})
            ),
            flush=True,
        )
        await wait_for_input(loop, abort_sem)
        return output(True, values={"push_updates": "finished"})

    rc = retrieve_commands(RemoteControl)
    if args.command in rc:
        await getattr(atv.remote_control, args.command)()
        return output(True, values={"command": args.command})

    return output(False, "unsupported_command")


async def appstart(loop):
    """Start the asyncio event loop and runs the application."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="command to run")
    parser.add_argument("-i", "--id", help="device identifier", dest="id", default=None)
    parser.add_argument(
        "--protocol",
        action=TransformProtocol,
        help="protocol to use (values: dmap, mrp)",
        dest="protocol",
        default=None,
    )
    parser.add_argument(
        "-s",
        "--scan-hosts",
        help="scan specific hosts",
        dest="scan_hosts",
        default=None,
        action=VerifyScanHosts,
    )
    parser.add_argument(
        "--output",
        help="output format (values: json)",
        dest="output",
        default=json.dumps,
        action=TransformOutput,
    )
    parser.add_argument(
        "--debug",
        help="save debug log to atvscript.log",
        action="store_true",
        dest="debug",
    )

    creds = parser.add_argument_group("credentials")
    creds.add_argument(
        "--dmap-credentials",
        help="DMAP credentials to device",
        dest="dmap_credentials",
        default=None,
    )
    creds.add_argument(
        "--mrp-credentials",
        help="MRP credentials to device",
        dest="mrp_credentials",
        default=None,
    )
    creds.add_argument(
        "--airplay-credentials",
        help="credentials for airplay",
        dest="airplay_credentials",
        default=None,
    )

    args = parser.parse_args()
    abort_sem = asyncio.Semaphore(0)

    if args.debug:
        # Only allow saving to file to make sure output always has the specified format
        logging.basicConfig(
            filename="atvscript.log",
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _handle_exception(loop, context):
        kwargs = {"error": context["message"]}
        if "exception" in context:
            kwargs["exception"] = context["exception"]

        print(args.output(output(False, **kwargs)))
        abort_sem.release()

    loop.set_exception_handler(_handle_exception)

    _LOGGER.debug("Started atvscript")

    try:
        print(args.output(await _handle_command(args, abort_sem, loop)), flush=True)
    except Exception as ex:
        print(args.output(output(False, exception=ex)), flush=True)

    return 0


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(appstart(loop))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
