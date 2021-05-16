"""Example of streaming a file and printing status updates.

python stream.py 10.0.0.4 file.mp3
"""

import asyncio
import sys

import pyatv
from pyatv.interface import Playing, PushListener

LOOP = asyncio.get_event_loop()


class PushUpdatePrinter(PushListener):
    """Print push updates to console."""

    def playstatus_update(self, updater, playstatus: Playing) -> None:
        """Inform about changes to what is currently playing."""
        print(30 * "-" + "\n", playstatus)

    def playstatus_error(self, updater, exception: Exception) -> None:
        """Inform about an error when updating play status."""
        print("Error:", exception)


async def stream_with_push_updates(
    address: str, filename: str, loop: asyncio.AbstractEventLoop
):
    """Find a device and print what is playing."""
    print("* Discovering device on network...")
    atvs = await pyatv.scan(loop, hosts=[address], timeout=5)

    if not atvs:
        print("* Device found", file=sys.stderr)
        return

    conf = atvs[0]

    print("* Connecting to", conf.address)
    atv = await pyatv.connect(conf, loop)

    listener = PushUpdatePrinter()
    atv.push_updater.listener = listener
    atv.push_updater.start()

    try:
        print("* Starting to stream", filename)
        await atv.stream.stream_file(filename)
        await asyncio.sleep(1)
    finally:
        atv.close()


if __name__ == "__main__":
    LOOP.run_until_complete(stream_with_push_updates(sys.argv[1], sys.argv[2], LOOP))
