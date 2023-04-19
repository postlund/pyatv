"""Various helper methods."""

import asyncio
from typing import Callable, Mapping, Optional

import miniaudio

import pyatv

HOMESHARING_SERVICE: str = "_appletv-v2._tcp.local"
DEVICE_SERVICE: str = "_touch-able._tcp.local"
MEDIAREMOTE_SERVICE: str = "_mediaremotetv._tcp.local"
AIRPLAY_SERVICE: str = "_airplay._tcp.local"
RAOP_SERVICE: str = "_raop._tcp.local"
HSCP_SERVICE: str = "_hscp._tcp.local"


async def auto_connect(
    handler: Callable[[pyatv.interface.AppleTV], None],
    timeout: int = 5,
    not_found: Optional[Callable[[], None]] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> None:
    """Connect to first discovered device.

    This is a convenience method that auto discovers devices, picks the first
    device found, connects to it and passes it to a user provided handler. An
    optional error handler can be provided that is called when no device was found.
    Very inflexible in many cases, but can be handys sometimes when trying things.

    Note: both handler and not_found must be coroutines
    """

    async def _handle(loop):
        atvs = await pyatv.scan(loop, timeout=timeout)

        # Take the first device found
        if atvs:
            atv = await pyatv.connect(atvs[0], loop)

            try:
                await handler(atv)
            finally:
                atv.close()
        else:
            if not_found is not None:
                await not_found()

    loop = loop or asyncio.get_event_loop()
    await _handle(loop)


def get_unique_id(  # pylint: disable=too-many-return-statements
    service_type: str, service_name: str, properties: Mapping[str, str]
) -> Optional[str]:
    """Return unique identifier from a Zeroconf service.

    `service_type` is the Zeroconf service type (e.g. *_mediaremotetv._tcp.local*),
    `service_name` name of the service (e.g. *Office* or *Living Room*) and
    `properties` all key-value properties belonging to the service.

    The unique identifier is returned if available, otherwise `None` is returned.
    """
    if service_type in [DEVICE_SERVICE, HOMESHARING_SERVICE]:
        return service_name.split("_")[0]
    if service_type == HSCP_SERVICE:
        return properties.get("Machine ID")
    if service_type == MEDIAREMOTE_SERVICE:
        return properties.get("UniqueIdentifier")
    if service_type == AIRPLAY_SERVICE:
        return properties.get("deviceid")
    if service_type == RAOP_SERVICE:
        split = service_name.split("@", maxsplit=1)

        # Normally a RAOP devices announces with "id@name" as zeroconf name. But some
        # devices seems to break from this behavior and just use "name", thus leaving
        # out the id. Some of these devices however have the public key ("pk")
        # available as an attribute so that can be used as an identifier in that case.
        if len(split) == 2:
            return split[0]
        return properties.get("pk")
    return None


async def is_streamable(filename: str) -> bool:
    """Return if a file is streamable by pyatv.

    This method will return if the file format of the given file is supported
    and streamable by pyatv. It will never raise an exception, e.g. because the
    file is missing or lack of permissions.
    """
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, miniaudio.get_file_info, filename)
    except Exception:
        return False
    return True
