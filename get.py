import aiohttp
import asyncio

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://10.0.10.81:7000/info") as resp:
            print(resp)

asyncio.run(main())