"""Example of playing a video file via AirPlay.

python play_url.py <id> <airplay credentials> <url>
"""

import asyncio
import sys

import pyatv
from pyatv.const import Protocol


async def play_url(device_id: str, airplay_credentials: str, url: str):
    """Connect to an Apple TV and stream file via AirPlay."""
    print("* Discovering device on network...")
    atvs = await pyatv.scan(identifier=device_id)
    if not atvs:
        print("* Device found", file=sys.stderr)
        return

    conf = atvs[0]
    conf.set_credentials(Protocol.AirPlay, airplay_credentials)
    atv = await pyatv.connect(conf)

    try:
        print(f"* Streaming {url} to {conf.address}")
        await atv.stream.play_url(url)
    finally:
        await atv.close()


if __name__ == "__main__":
    asyncio.run(play_url(sys.argv[1], sys.argv[2], sys.argv[3]))
