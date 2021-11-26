"""Example of streaming a file and printing status updates.

python stream.py 10.0.0.4 file.mp3
"""
import io
import asyncio
import aiohttp
import sys

import pyatv
from pyatv.interface import Playing, PushListener

LOOP = asyncio.get_event_loop()

URL = "https://file-examples-com.github.io/uploads/2017/11/file_example_MP3_1MG.mp3"

class TestBuffer(io.BufferedIOBase):

    def __init__(self, source):
        self.source = source

    @property
    def seekable(self):
        return False

    def read(self, count):
        return self.source.read(count)

class PushUpdatePrinter(PushListener):
    """Print push updates to console."""

    def playstatus_update(self, updater, playstatus: Playing) -> None:
        """Inform about changes to what is currently playing."""
        print(30 * "-" + "\n", playstatus)

    def playstatus_error(self, updater, exception: Exception) -> None:
        """Inform about an error when updating play status."""
        print("Error:", exception)

async def stream_with_push_updates(
    address: str, loop: asyncio.AbstractEventLoop
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
    LOOP.run_until_complete(stream_with_push_updates(sys.argv[1], LOOP))
