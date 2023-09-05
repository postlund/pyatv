"""Simple example using file based storage."""

import asyncio
import sys

from pyatv import connect, scan
from pyatv.storage.file_storage import FileStorage

LOOP = asyncio.get_event_loop()


async def connect_with_storage(host):
    """Connect to a device using a storage."""
    loop = asyncio.get_event_loop()

    # Load the same storage that pyatv uses internally (e.g. in atvremote)
    storage = FileStorage.default_storage(loop)
    await storage.load()

    atvs = await scan(loop, timeout=5, hosts=[host], storage=storage)

    if not atvs:
        print("Device not found", file=sys.stderr)
        return

    atv = await connect(atvs[0], loop, storage=storage)
    print(await atv.metadata.playing())

    atv.close()


if __name__ == "__main__":
    asyncio.run(connect_with_storage(sys.argv[1]))
