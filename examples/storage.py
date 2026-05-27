"""Simple example using file based storage."""

import asyncio
import sys

from pyatv import connect, scan
from pyatv.storage.file_storage import FileStorage


async def connect_with_storage(host):
    """Connect to a device using a storage."""
    # Load the same storage that pyatv uses internally (e.g. in atvremote)
    storage = FileStorage.default_storage(asyncio.get_running_loop())
    await storage.load()

    atvs = await scan(timeout=5, hosts=[host], storage=storage)

    if not atvs:
        print("Device not found", file=sys.stderr)
        return

    atv = await connect(atvs[0], storage=storage)
    print(await atv.metadata.playing())

    atv.close()


if __name__ == "__main__":
    asyncio.run(connect_with_storage(sys.argv[1]))
