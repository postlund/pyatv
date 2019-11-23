"""CLI application for discovering and controlling Apple TVs."""

import sys
import inspect
import logging
import binascii
import asyncio

import argparse
from argparse import ArgumentTypeError

import pyatv
from pyatv import (const, exceptions, interface)
from pyatv.conf import (
    AppleTV, DmapService, MrpService, AirPlayService)
from pyatv.dmap import tag_definitions
from pyatv.dmap.parser import pprint
from pyatv.interface import retrieve_commands


def _print_commands(title, api):
    cmd_list = retrieve_commands(api)
    commands = ' - ' + '\n - '.join(
        map(lambda x: x[0] + ' - ' + x[1], sorted(cmd_list.items())))
    print('{} commands:\n{}\n'.format(title, commands))


async def _read_input(loop, prompt):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    user_input = await loop.run_in_executor(None, sys.stdin.readline)
    return user_input.strip()


async def _scan_for_device(args, timeout, loop, protocol=None):
    options = {
        'timeout': timeout,
        'protocol': protocol
    }

    if not args.name:
        options['identifier'] = args.id

    atvs = await pyatv.scan(loop, **options)
    if not atvs:
        logging.error('Could not find any Apple TV on current network')
        return None

    if args.name:
        devices = [atv for atv in atvs if atv.name == args.name]
    else:
        devices = atvs

    if len(devices) > 1:
        logging.error(
            'Found more than one Apple TV; specify one using --id')
        _print_found_apple_tvs(devices, outstream=sys.stderr)
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
        _print_commands('Remote control', interface.RemoteControl)
        _print_commands('Metadata', interface.Metadata)
        _print_commands('Playing', interface.Playing)
        _print_commands('AirPlay', interface.AirPlay)
        _print_commands('Device', DeviceCommands)
        _print_commands('Global', self.__class__)

        return 0

    async def help(self):
        """Print help text for a command."""
        if len(self.args.command) != 2:
            print('Which command do you want help with?', file=sys.stderr)
            return 1

        iface = [interface.RemoteControl,
                 interface.Metadata,
                 interface.Playing,
                 interface.AirPlay,
                 self.__class__,
                 DeviceCommands]
        for cmd in iface:
            for key, value in cmd.__dict__.items():
                if key.startswith('_') or key != self.args.command[1]:
                    continue

                if inspect.isfunction(value):
                    signature = inspect.signature(value)
                else:
                    signature = ' (property)'

                print('COMMAND:\n>> {0}{1}\n\nHELP:\n{2}'.format(
                    key, signature, inspect.getdoc(value)))
        return 0

    async def scan(self):
        """Scan for Apple TVs on the network."""
        atvs = await pyatv.scan(self.loop, timeout=self.args.scan_timeout)
        _print_found_apple_tvs(atvs)

        return 0

    async def pair(self):
        """Pair pyatv as a remote control with an Apple TV."""
        if self.args.protocol is None:
            logging.error('No protocol specified')
            return 1

        apple_tv = await _scan_for_device(
            self.args, self.args.scan_timeout, self.loop)
        if not apple_tv:
            return 2

        options = {}

        # Protocol specific options
        if self.args.protocol == const.PROTOCOL_DMAP:
            options.update({
                'pairing_guid': self.args.pairing_guid,
                'remote_name': self.args.remote_name,
            })

        pairing = await pyatv.pair(
            apple_tv, self.args.protocol, self.loop, **options)

        try:
            await self._perform_pairing(pairing)
        except:  # pylint: disable=bare-except  # noqa
            logging.exception('Pairing failed')
            return 3
        finally:
            await pairing.close()

        return 0

    async def _perform_pairing(self, pairing):
        await pairing.begin()

        # Ask for PIN if present or just wait for pairing to end
        if pairing.device_provides_pin:
            pin = await _read_input(self.loop, 'Enter PIN on screen: ')
            pairing.pin(pin)
        else:
            pairing.pin(self.args.pin_code)

            if self.args.pin_code is None:
                print('Use any pin to pair with "{}"'
                      ' (press ENTER to stop)'.format(
                          self.args.remote_name))
            else:
                print('Use pin {} to pair with "{}"'
                      ' (press ENTER to stop)'.format(
                          self.args.pin_code, self.args.remote_name))

            await self.loop.run_in_executor(None, sys.stdin.readline)

        await pairing.finish()

        # Give some feedback to the user
        if pairing.has_paired:
            print('Pairing seems to have succeeded, yey!')
            print('You may now use these credentials: {0}'.format(
                pairing.service.credentials))
        else:
            print('Pairing failed!')


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
        print('Enter commands and press enter')
        print('Type help for help and exit to quit')

        while True:
            command = await _read_input(self.loop, 'pyatv> ')
            if command.lower() == 'exit':
                break
            elif command == 'cli':
                print('Command not availble here')
                continue

            await _handle_device_command(
                self.args, command, self.atv, self.loop)

    async def artwork_save(self):
        """Download artwork and save it to artwork.png."""
        artwork = await self.atv.metadata.artwork()
        if artwork is not None:
            with open('artwork.png', 'wb') as file:
                file.write(artwork)
        else:
            print('No artwork is currently available.')
            return 1
        return 0

    async def push_updates(self):
        """Listen for push updates."""
        print('Press ENTER to stop')

        self.atv.push_updater.start()
        await self.loop.run_in_executor(None, sys.stdin.readline)
        self.atv.push_updater.stop()
        return 0


class PushListener:
    """Internal listener for push updates."""

    @staticmethod
    def playstatus_update(_, playstatus):
        """Print what is currently playing when it changes."""
        print(str(playstatus), flush=True)
        print(20*'-', flush=True)

    @staticmethod
    def playstatus_error(updater, exception):
        """Inform about an error and restart push updates."""
        print("An error occurred (restarting): {0}".format(exception))
        updater.start(initial_delay=1)


def _in_range(lower, upper, allow_none=False):
    def _checker(value):
        if allow_none and str(value).lower() == 'none':
            return None
        if int(value) >= lower and int(value) < upper:
            return int(value)
        raise ArgumentTypeError('Must be greater >= {} and < {}'.format(
            lower, upper))
    return _checker


# pylint: disable=too-few-public-methods
class TransformProtocol(argparse.Action):
    """Transform protocol in string format to internal representation."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Match protocol string and save correct version."""
        if values == "mrp":
            setattr(namespace, self.dest, const.PROTOCOL_MRP)
        elif values == "dmap":
            setattr(namespace, self.dest, const.PROTOCOL_DMAP)
        elif values == 'airplay':
            setattr(namespace, self.dest, const.PROTOCOL_AIRPLAY)
        else:
            raise ArgumentTypeError('Valid protocols are: mrp, dmap, airplay')


async def cli_handler(loop):
    """Application starts here."""
    parser = argparse.ArgumentParser()

    parser.add_argument('command', nargs='+',
                        help='commands, help, ...')
    parser.add_argument('-i', '--id', help='device identifier',
                        dest='id', default=None)
    parser.add_argument('-n', '--name', help='apple tv name',
                        dest='name', default=None)
    parser.add_argument('--address', help='device ip address or hostname',
                        dest='address', default=None)
    parser.add_argument('--protocol', action=TransformProtocol,
                        help='protocol to use (values: dmap, mrp)',
                        dest='protocol', default=None)
    parser.add_argument('--port', help='port when connecting',
                        dest='port', type=_in_range(0, 65535),
                        default=0)
    parser.add_argument('-t', '--scan-timeout', help='timeout when scanning',
                        dest='scan_timeout', type=_in_range(1, 100),
                        metavar='TIMEOUT', default=3)
    parser.add_argument('--version', action='version',
                        help='version of atvremote and pyatv',
                        version='%(prog)s {0}'.format(const.__version__))

    pairing = parser.add_argument_group('pairing')
    pairing.add_argument('--remote-name', help='remote pairing name',
                         dest='remote_name', default='pyatv')
    pairing.add_argument('-p', '--pin', help='pairing pin code',
                         dest='pin_code', metavar='PIN', default=1234,
                         type=_in_range(0, 9999, allow_none=True))
    pairing.add_argument('--pairing-guid',
                         help='pairing guid (16 chars hex)',
                         dest='pairing_guid', default=None)

    parser.add_argument('-m', '--manual', action='store_true',
                        help='use manual device details',
                        dest='manual', default=False)

    creds = parser.add_argument_group('credentials')
    creds.add_argument('--dmap-credentials', help='DMAP credentials to device',
                       dest='dmap_credentials', default=None)
    creds.add_argument('--mrp-credentials', help='MRP credentials to device',
                       dest='mrp_credentials', default=None)
    creds.add_argument('--airplay-credentials',
                       help='credentials for airplay',
                       dest='airplay_credentials', default=None)

    debug = parser.add_argument_group('debugging')
    debug.add_argument('-v', '--verbose', help='increase output verbosity',
                       action='store_true', dest='verbose')
    debug.add_argument('--debug', help='print debug information',
                       action='store_true', dest='debug')

    args = parser.parse_args()
    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    logging.basicConfig(level=loglevel,
                        format='%(levelname)s: %(message)s')
    logging.getLogger('requests').setLevel(logging.WARNING)

    cmds = retrieve_commands(GlobalCommands)

    if args.command[0] in cmds:
        glob_cmds = GlobalCommands(args, loop)
        return (await _exec_command(
            glob_cmds, args.command[0], print_result=False))
    if not args.manual:
        if not await _autodiscover_device(args, loop):
            return 1

        return await _handle_commands(args, loop)

    if args.port == 0 or args.address is None or args.protocol is None:
        logging.error(
            'You must specify address, port and protocol in manual mode')
        return 1

    return await _handle_commands(args, loop)


def _print_found_apple_tvs(atvs, outstream=sys.stdout):
    print('Scan Results', file=outstream)
    print('=' * 40, file=outstream)
    for apple_tv in atvs:
        print('{0}\n'.format(apple_tv), file=outstream)


async def _autodiscover_device(args, loop):
    apple_tv = await _scan_for_device(
        args, args.scan_timeout, loop, protocol=args.protocol)
    if not apple_tv:
        return None

    service = apple_tv.main_service()

    # Common parameters for all protocols
    args.id = apple_tv.identifier
    args.address = apple_tv.address
    args.name = apple_tv.name
    args.protocol = service.protocol
    args.port = service.port

    def _set_credentials(protocol, field):
        service = apple_tv.get_service(protocol)
        if service:
            value = service.credentials or getattr(args, field)
            setattr(args, field, value)

    _set_credentials(const.PROTOCOL_DMAP, 'dmap_credentials')
    _set_credentials(const.PROTOCOL_MRP, 'mrp_credentials')
    _set_credentials(const.PROTOCOL_AIRPLAY, 'airplay_credentials')

    logging.info('Auto-discovered %s at %s', args.name, args.address)

    return apple_tv


def _extract_command_with_args(cmd):
    """Parse input command with arguments.

    Parses the input command in such a way that the user may
    provide additional argument to the command. The format used is this:
      command=arg1,arg2,arg3,...
    all the additional arguments are passed as arguments to the target
    method.
    """
    def _isint(value):
        try:
            int(value)
            return True
        except ValueError:
            return False

    equal_sign = cmd.find('=')
    if equal_sign == -1:
        return cmd, []

    command = cmd[0:equal_sign]
    args = cmd[equal_sign+1:].split(',')
    converted = [x if not _isint(x) else int(x) for x in args]
    return command, converted


async def _handle_commands(args, loop):
    config = AppleTV(args.address, args.name)
    if args.dmap_credentials or args.protocol == const.PROTOCOL_DMAP:
        config.add_service(DmapService(
            args.id, args.dmap_credentials, port=args.port))
    if args.mrp_credentials or args.protocol == const.PROTOCOL_MRP:
        config.add_service(MrpService(
            args.id, args.port, credentials=args.mrp_credentials))
    if args.airplay_credentials:
        config.add_service(AirPlayService(
            args.id, credentials=args.airplay_credentials))

    atv = await pyatv.connect(config, loop, protocol=args.protocol)
    atv.push_updater.listener = PushListener()

    try:
        for cmd in args.command:
            ret = await _handle_device_command(args, cmd, atv, loop)
            if ret != 0:
                return ret
    finally:
        await atv.close()

    return 0


# pylint: disable=too-many-return-statements
async def _handle_device_command(args, cmd, atv, loop):
    device = retrieve_commands(DeviceCommands)
    ctrl = retrieve_commands(interface.RemoteControl)
    metadata = retrieve_commands(interface.Metadata)
    playing = retrieve_commands(interface.Playing)
    airplay = retrieve_commands(interface.AirPlay)

    # Parse input command and argument from user
    cmd, cmd_args = _extract_command_with_args(cmd)
    if cmd in device:
        return (await _exec_command(
            DeviceCommands(atv, loop, args), cmd, False, *cmd_args))

    if cmd in ctrl:
        return (await _exec_command(
            atv.remote_control, cmd, True, *cmd_args))

    if cmd in metadata:
        return (await _exec_command(
            atv.metadata, cmd, True, *cmd_args))

    if cmd in playing:
        playing_resp = await atv.metadata.playing()
        return (await _exec_command(
            playing_resp, cmd, True, *cmd_args))

    if cmd in airplay:
        return (await _exec_command(
            atv.airplay, cmd, True, *cmd_args))

    logging.error('Unknown command: %s', cmd)
    return 1


async def _exec_command(obj, command, print_result, *args):
    try:
        # If the command to execute is a @property, the value returned by that
        # property will be stored in tmp. Otherwise it's a coroutine and we
        # have to yield for the result and wait until it is available.
        tmp = getattr(obj, command)
        if inspect.ismethod(tmp):
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
        logging.exception("Command '%s' is not supported by device", command)
    except exceptions.AuthenticationError as ex:
        logging.exception('Authentication error: %s', str(ex))
    return 1


def _pretty_print(data):
    if data is None:
        return
    if isinstance(data, bytes):
        print(binascii.hexlify(data))
    elif isinstance(data, list):
        print(pprint(data, tag_definitions.lookup_tag))
    else:
        print(data)


def main():
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

        except:  # pylint: disable=bare-except  # noqa
            import traceback

            traceback.print_exc(file=sys.stderr)
            sys.stderr.writelines(
                '\n>>> An error occurred, full stack trace above\n')

        return 1

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_run_application(loop))
    except KeyboardInterrupt:
        pass

    return 1


if __name__ == '__main__':
    sys.exit(main())
