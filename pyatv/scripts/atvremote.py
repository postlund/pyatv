"""CLI application for discovering and controlling Apple TVs."""

import argparse
import asyncio
import binascii
import inspect
from ipaddress import IPv4Address
import logging
import sys
import traceback

from pyatv import connect, const, exceptions, interface, pair, scan
from pyatv.conf import AppleTV, ManualService
from pyatv.const import (
    FeatureName,
    FeatureState,
    InputAction,
    Protocol,
    RepeatState,
    ShuffleState,
)
from pyatv.interface import retrieve_commands
from pyatv.scripts import (
    TransformIdentifiers,
    TransformProtocol,
    VerifyScanHosts,
    VerifyScanProtocols,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0


def _print_commands(title, api):
    cmd_list = retrieve_commands(api)
    commands = " - " + "\n - ".join(
        map(lambda x: x[0] + " - " + x[1], sorted(cmd_list.items()))
    )
    print(f"{title} commands:\n{commands}\n")


async def _read_input(loop: asyncio.AbstractEventLoop, prompt: str):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    user_input = await loop.run_in_executor(None, sys.stdin.readline)
    return user_input.strip()


async def _scan_for_device(args, timeout, loop, protocol=None):
    options = {"timeout": timeout, "protocol": protocol}

    if not args.name:
        options["identifier"] = args.id
    if args.scan_hosts:
        options["hosts"] = args.scan_hosts

    atvs = await scan(loop, **options)

    if args.name:
        devices = [atv for atv in atvs if atv.name == args.name]
    else:
        devices = atvs

    if not atvs:
        _LOGGER.error("Could not find any Apple TV on current network")
        return None

    if len(devices) > 1:
        _LOGGER.error("Found more than one Apple TV; specify one using --id")
        _print_found_apple_tvs(devices, sys.stderr)
        return None

    return devices[0]


class GlobalCommands:
    """Commands not bound to a specific device."""

    def __init__(self, args, loop):
        """Initialize a new instance of GlobalCommands."""
        self.args = args
        self.loop = loop

    async def commands(self):
        """Print a list with available commands."""
        _print_commands("Remote control", interface.RemoteControl)
        _print_commands("Metadata", interface.Metadata)
        _print_commands("Power", interface.Power)
        _print_commands("Playing", interface.Playing)
        _print_commands("AirPlay", interface.Stream)
        _print_commands("Device Info", interface.DeviceInfo)
        _print_commands("Device", DeviceCommands)
        _print_commands("Apps", interface.Apps)
        _print_commands("Global", self.__class__)

        return 0

    async def help(self):
        """Print help text for a command."""
        if len(self.args.command) != 2:
            print("Which command do you want help with?", file=sys.stderr)
            return 1

        iface = [
            interface.RemoteControl,
            interface.Metadata,
            interface.Power,
            interface.Playing,
            interface.Stream,
            interface.DeviceInfo,
            interface.Apps,
            interface.Audio,
            self.__class__,
            DeviceCommands,
        ]
        for cmd in iface:
            for key, value in cmd.__dict__.items():
                if key.startswith("_") or key != self.args.command[1]:
                    continue

                if inspect.isfunction(value):
                    signature = inspect.signature(value)
                else:
                    signature = " (property)"

                print(
                    f"COMMAND:\n>> {key}{signature}\n\nHELP:\n{inspect.getdoc(value)}"
                )
        return 0

    async def scan(self):
        """Scan for Apple TVs on the network."""
        atvs = await scan(
            self.loop,
            hosts=self.args.scan_hosts,
            timeout=self.args.scan_timeout,
            protocol=self.args.scan_protocols,
            identifier=self.args.id,
        )
        _print_found_apple_tvs(atvs, sys.stdout)

        return 0

    async def pair(self):
        """Pair pyatv as a remote control with an Apple TV."""
        if self.args.protocol is None:
            _LOGGER.error("No protocol specified")
            return 1

        if self.args.manual:
            conf = _manual_device(self.args)
        else:
            conf = await _scan_for_device(self.args, self.args.scan_timeout, self.loop)
        if not conf:
            return 2

        options = {}

        # Inject user provided credentials
        for proto in Protocol:
            conf.set_credentials(
                proto, getattr(self.args, f"{proto.name.lower()}_credentials")
            )

        # Protocol specific options
        if self.args.protocol == const.Protocol.DMAP:
            options.update(
                {
                    "pairing_guid": self.args.pairing_guid,
                    "remote_name": self.args.remote_name,
                }
            )

        pairing = await pair(conf, self.args.protocol, self.loop, **options)

        try:
            await self._perform_pairing(pairing)
        except Exception:  # pylint: disable=broad-except  # noqa
            _LOGGER.exception("Pairing failed")
            return 3
        finally:
            await pairing.close()

        return 0

    async def _perform_pairing(self, pairing):
        await pairing.begin()

        # Ask for PIN if present or just wait for pairing to end
        if pairing.device_provides_pin:
            pin = await _read_input(self.loop, "Enter PIN on screen: ")
            pairing.pin(pin)
        else:
            pairing.pin(self.args.pin_code)

            if self.args.pin_code is None:
                print(
                    f'Use any pin to pair with "{self.args.remote_name}"'
                    " (press ENTER to stop)"
                )
            else:
                print(
                    f"Use pin {self.args.pin_code} to pair "
                    f'with "{self.args.remote_name}"'
                    " (press ENTER to stop)"
                )

            await self.loop.run_in_executor(None, sys.stdin.readline)

        await pairing.finish()

        # Give some feedback to the user
        if pairing.has_paired:
            print("Pairing seems to have succeeded, yey!")
            print(f"You may now use these credentials: {pairing.service.credentials}")
        else:
            print("Pairing failed!")


class DeviceCommands:
    """Additional commands available for a device.

    These commands are not part of the API but are provided by atvremote.
    """

    def __init__(self, atv, loop, args):
        """Initialize a new instance of DeviceCommands."""
        self.atv = atv
        self.loop = loop
        self.args = args

    async def cli(self):
        """Enter commands in a simple CLI."""
        print("Enter commands and press enter")
        print("Type help for help and exit to quit")

        while True:
            command = await _read_input(self.loop, "pyatv> ")
            if command.lower() == "exit":
                break

            if command == "cli":
                print("Command not available here")
                continue

            await _handle_device_command(self.args, command, self.atv, self.loop)

    async def artwork_save(self, width=None, height=None):
        """Download artwork and save it to artwork.png."""
        artwork = await self.atv.metadata.artwork(width=width, height=height)
        if artwork is not None:
            with open("artwork.png", "wb") as file:
                file.write(artwork.bytes)
        else:
            print("No artwork is currently available.")
            return 1
        return 0

    async def push_updates(self):
        """Listen for push updates."""
        if not self.atv.features.in_state(
            FeatureState.Available, FeatureName.PushUpdates
        ):
            print("Push updates are not supported (no protocol supports it)")
            return 1

        print("Press ENTER to stop")

        self.atv.push_updater.start()
        await self.loop.run_in_executor(None, sys.stdin.readline)
        self.atv.push_updater.stop()
        return 0

    async def device_info(self):
        """Print various information about the device."""
        devinfo = self.atv.device_info
        print("Model/SW:", devinfo)
        print("     MAC:", devinfo.mac)
        return 0

    async def features(self) -> int:
        """Print a list of all features and options."""
        unsupported = bool(
            len(self.args.command) == 2 and self.args.command[1] == "all"
        )
        all_features = self.atv.features.all_features(include_unsupported=unsupported)

        print("Feature list:")
        print("-------------")
        for name, feature in all_features.items():
            output = f"{name.name}: {feature.state.name}"
            options = [f"{k}={v}" for k, v in feature.options.items()]
            if options:
                output += f", Options={', '.join(options)}"
            print(output)

        print("\nLegend:")
        print("-------")
        print("Available: Supported by device and usable now")
        print("Unavailable: Supported by device but not usable now")
        print("Unknown: Supported by the device but availability not known")
        print("Unsupported: Not supported by this device (or by pyatv)")
        return 0

    async def delay(self, delay_time: int):
        """Sleep for a certain amount if milliseconds."""
        await asyncio.sleep(float(delay_time) / 1000.0)
        return 0


class PushListener(interface.PushListener):
    """Internal listener for push updates."""

    @staticmethod
    def playstatus_update(_, playstatus):
        """Print what is currently playing when it changes."""
        print(str(playstatus), flush=True)
        print(20 * "-", flush=True)

    @staticmethod
    def playstatus_error(_, exception):
        """Inform about an error and restart push updates."""
        print(f"An error occurred (restarting): {exception}")


class DeviceListener(interface.DeviceListener):
    """Internal listener for generic device updates."""

    def connection_lost(self, exception):
        """Call when unexpectedly being disconnected from device."""
        print("Connection lost, stack trace below:", file=sys.stderr)
        traceback.print_tb(exception.__traceback__, file=sys.stderr)

    def connection_closed(self):
        """Call when connection was (intentionally) closed."""
        _LOGGER.debug("Connection was closed properly")


def _in_range(lower, upper, allow_none=False):
    def _checker(value):
        if allow_none and str(value).lower() == "none":
            return None
        if int(value) >= lower and int(value) < upper:
            return int(value)
        raise argparse.ArgumentTypeError(f"Must be greater >= {lower} and < {upper}")

    return _checker


async def cli_handler(loop):
    """Application starts here."""
    parser = argparse.ArgumentParser()

    parser.add_argument("command", nargs="+", help="commands, help, ...")
    parser.add_argument(
        "-i",
        "--id",
        help="device identifier",
        dest="id",
        action=TransformIdentifiers,
        default=None,
    )
    parser.add_argument("-n", "--name", help="apple tv name", dest="name", default=None)
    parser.add_argument(
        "--address", help="device ip address or hostname", dest="address", default=None
    )
    parser.add_argument(
        "--protocol",
        action=TransformProtocol,
        help="protocol to use (values: dmap, mrp)",
        dest="protocol",
        default=None,
    )
    parser.add_argument(
        "--port",
        help="port when connecting",
        dest="port",
        type=_in_range(0, 65535),
        default=0,
    )
    parser.add_argument(
        "-t",
        "--scan-timeout",
        help="timeout when scanning",
        dest="scan_timeout",
        type=_in_range(1, 100),
        metavar="TIMEOUT",
        default=3,
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
        "--scan-protocols",
        help="scan for specific protocols",
        dest="scan_protocols",
        default=None,
        action=VerifyScanProtocols,
    )
    parser.add_argument(
        "--version",
        action="version",
        help="version of atvremote and pyatv",
        version=f"%(prog)s {const.__version__}",
    )

    pairing = parser.add_argument_group("pairing")
    pairing.add_argument(
        "--remote-name", help="remote pairing name", dest="remote_name", default="pyatv"
    )
    pairing.add_argument(
        "-p",
        "--pin",
        help="pairing pin code",
        dest="pin_code",
        metavar="PIN",
        default=1234,
        type=_in_range(0, 9999, allow_none=True),
    )
    pairing.add_argument(
        "--pairing-guid",
        help="pairing guid (16 chars hex)",
        dest="pairing_guid",
        default=None,
    )

    parser.add_argument(
        "-m",
        "--manual",
        action="store_true",
        help="use manual device details",
        dest="manual",
        default=False,
    )

    parser.add_argument(
        "--raop-password",
        help="optional password for raop",
        dest="raop_password",
        default=None,
    )

    creds = parser.add_argument_group("credentials")
    for prot in Protocol:
        creds.add_argument(
            f"--{prot.name.lower()}-credentials",
            help=f"credentials for {prot.name}",
            dest=f"{prot.name.lower()}_credentials",
            default=None,
        )

    debug = parser.add_argument_group("debugging")
    debug.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
        dest="verbose",
    )
    debug.add_argument(
        "--debug", help="print debug information", action="store_true", dest="debug"
    )
    debug.add_argument(
        "--mdns-debug",
        help="print mdns debug data",
        action="store_true",
        dest="mdns_debug",
    )

    args = parser.parse_args()
    if args.manual and isinstance(args.id, list):
        parser.error("--manual only supports one identifier to --id")

    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    logging.basicConfig(
        level=loglevel,
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="%(asctime)s %(levelname)s [%(name)s]: %(message)s",
    )
    logging.getLogger("requests").setLevel(logging.WARNING)

    if args.mdns_debug:
        # logging.TRAFFIC is set in runtime by support.mdns
        logging.getLogger(
            "pyatv.core.mdns"
        ).level = logging.TRAFFIC  # pylint: disable=no-member

    cmds = retrieve_commands(GlobalCommands)

    if args.command[0] in cmds:
        glob_cmds = GlobalCommands(args, loop)
        return await _exec_command(glob_cmds, args.command[0], print_result=False)
    if not args.manual:
        config = await _autodiscover_device(args, loop)
        if not config:
            return 1

        return await _handle_commands(args, config, loop)

    if args.port == 0 or args.address is None or args.protocol is None:
        _LOGGER.error("You must specify address, port and protocol in manual mode")
        return 1

    config = _manual_device(args)
    return await _handle_commands(args, config, loop)


def _print_found_apple_tvs(atvs, outstream):
    print("Scan Results", file=outstream)
    print("=" * 40, file=outstream)
    for apple_tv in atvs:
        print(f"{apple_tv}\n", file=outstream)


async def _autodiscover_device(args, loop):
    apple_tv = await _scan_for_device(
        args, args.scan_timeout, loop, protocol=args.scan_protocols
    )
    if not apple_tv:
        return None

    def _set_credentials(protocol, field):
        service = apple_tv.get_service(protocol)
        if service:
            value = service.credentials or getattr(args, field)
            service.credentials = value

    for proto in Protocol:
        _set_credentials(proto, f"{proto.name.lower()}_credentials")

    raop_service = apple_tv.get_service(Protocol.RAOP)
    if raop_service:
        raop_service.password = args.raop_password

    _LOGGER.info("Auto-discovered %s at %s", apple_tv.name, apple_tv.address)

    return apple_tv


def _manual_device(args):
    config = AppleTV(IPv4Address(args.address), args.name)
    service = ManualService(args.id, args.protocol, args.port, {})
    service.credentials = getattr(args, f"{args.protocol.name.lower()}_credentials")
    service.password = args.raop_password
    config.add_service(service)
    return config


def _extract_command_with_args(cmd):
    """Parse input command with arguments.

    Parses the input command in such a way that the user may
    provide additional argument to the command. The format used is this:
      command=arg1,arg2,arg3,...
    all the additional arguments are passed as arguments to the target
    method.
    """

    def _typeparse(value):
        try:
            return int(value)
        except ValueError:
            return value

    def _parse_args(cmd, args):
        args = [_typeparse(x) for x in args]
        if cmd == "set_shuffle":
            return [ShuffleState(args[0])]
        if cmd == "set_repeat":
            return [RepeatState(args[0])]
        if cmd in ["up", "down", "left", "right", "select", "menu", "home"]:
            return [InputAction(args[0])]
        if cmd == "set_volume":
            return [float(args[0])]
        return args

    equal_sign = cmd.find("=")
    if equal_sign == -1:
        return cmd, []

    command = cmd[0:equal_sign]
    args = cmd[equal_sign + 1 :].split(",")
    return command, _parse_args(command, args)


async def _handle_commands(args, config, loop):
    device_listener = DeviceListener()
    push_listener = PushListener()
    atv = await connect(config, loop, protocol=args.protocol)
    atv.listener = device_listener

    if atv.features.in_state(FeatureState.Available, FeatureName.PushUpdates):
        atv.push_updater.listener = push_listener
    else:
        print("NOTE: Push updates are not supported in this configuration")

    try:
        for cmd in args.command:
            ret = await _handle_device_command(args, cmd, atv, loop)
            if ret != 0:
                return ret
    finally:
        remaining_tasks = atv.close()
        _LOGGER.debug("Waiting for %d remaining tasks", len(remaining_tasks))
        await asyncio.wait_for(asyncio.gather(*remaining_tasks), DEFAULT_TIMEOUT)
    return 0


# pylint: disable=too-many-return-statements
async def _handle_device_command(args, cmd, atv, loop):
    device = retrieve_commands(DeviceCommands)
    ctrl = retrieve_commands(interface.RemoteControl)
    metadata = retrieve_commands(interface.Metadata)
    power = retrieve_commands(interface.Power)
    playing = retrieve_commands(interface.Playing)
    stream = retrieve_commands(interface.Stream)
    device_info = retrieve_commands(interface.DeviceInfo)
    apps = retrieve_commands(interface.Apps)
    audio = retrieve_commands(interface.Audio)

    # Parse input command and argument from user
    cmd, cmd_args = _extract_command_with_args(cmd)
    if cmd in device:
        return await _exec_command(
            DeviceCommands(atv, loop, args), cmd, False, *cmd_args
        )

    # NB: Needs to be above RemoteControl for now as volume_up/down exists in both
    # but implementations in Audio shall be called
    if cmd in audio:
        return await _exec_command(atv.audio, cmd, True, *cmd_args)

    if cmd in ctrl:
        return await _exec_command(atv.remote_control, cmd, True, *cmd_args)

    if cmd in metadata:
        return await _exec_command(atv.metadata, cmd, True, *cmd_args)

    if cmd in power:
        return await _exec_command(atv.power, cmd, True, *cmd_args)

    if cmd in playing:
        playing_resp = await atv.metadata.playing()
        return await _exec_command(playing_resp, cmd, True, *cmd_args)

    if cmd in stream:
        return await _exec_command(atv.stream, cmd, True, *cmd_args)

    if cmd in device_info:
        return await _exec_command(atv.device_info, cmd, True, *cmd_args)

    if cmd in apps:
        return await _exec_command(atv.apps, cmd, True, *cmd_args)

    _LOGGER.error("Unknown command: %s", cmd)
    return 1


async def _exec_command(obj, command, print_result, *args):
    try:
        # If the command to execute is a @property, the value returned by that
        # property will be stored in tmp. Otherwise it's a coroutine and we
        # have to yield for the result and wait until it is available.
        tmp = getattr(obj, command)
        if inspect.ismethod(tmp):
            # Special case for stream_file: if - is passed as input file, use stdin
            # as source instead of passing filename
            if command == interface.Stream.stream_file.__name__ and args[0] == "-":
                args = [sys.stdin.buffer, *args[1:]]
            value = await tmp(*args)
        else:
            value = tmp

        # Some commands might produce output themselves (especially non-API
        # commands), so don't print the return code they might give
        if print_result:
            _pretty_print(value)
            return 0
        return value
    except NotImplementedError:
        _LOGGER.exception("Command '%s' is not supported by device", command)
    except exceptions.AuthenticationError as ex:
        _LOGGER.exception("Authentication error: %s", str(ex))
    return 1


def _pretty_print(data):
    if data is None:
        return
    if isinstance(data, bytes):
        print(binascii.hexlify(data))
    elif isinstance(data, list):
        print(", ".join([str(item) for item in data]))
    else:
        print(data)


async def appstart(loop):
    """Start the asyncio event loop and runs the application."""
    # Helper method so that the coroutine exits cleanly if an exception
    # happens (which would leave resources dangling)
    async def _run_application(loop):
        try:
            return await cli_handler(loop)

        except KeyboardInterrupt:
            pass  # User pressed Ctrl+C, just ignore it

        except SystemExit:
            pass  # sys.exit() was used - do nothing

        except Exception:  # pylint: disable=broad-except  # noqa
            traceback.print_exc(file=sys.stderr)
            sys.stderr.writelines("\n>>> An error occurred, full stack trace above\n")

        return 1

    try:
        return await _run_application(loop)
    except KeyboardInterrupt:
        pass

    return 1


def main():
    """Application start here."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(appstart(loop))


if __name__ == "__main__":
    sys.exit(main())
