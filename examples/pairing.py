"""Simple example showing of pairing."""
import asyncio
import sys

from pyatv import pair, scan
from pyatv.const import PairingRequirement, Protocol


async def pair_protocol(atv, service):
    """Perform pairing for a single protocol."""
    print(f"Starting to pair protocol {service.protocol.name}")
    pairing = await pair(atv, Protocol.AirPlay, asyncio.get_event_loop())
    try:
        await pairing.begin()

        if pairing.device_provides_pin:
            pin = int(input("Enter PIN: "))
            pairing.pin(pin)
        else:
            pairing.pin(1234)  # Should be randomized
            input("Enter this PIN on the device: 1234")

        await pairing.finish()

    except Exception as ex:  # Check more specific exceptions here
        print("Pairing failed:", ex, file=sys.stderr)
    finally:
        await pairing.close()

    # Give some feedback about the process
    if pairing.has_paired:
        print("Paired with device!")
        print("Credentials:", pairing.service.credentials)
    else:
        print("Did not pair with device!")


async def main():
    """Script starts here."""
    confs = await scan(asyncio.get_event_loop(), hosts=["10.0.10.81"])
    if not confs:
        print("Did not find device!", file=sys.stderr)

    for service in confs[0].services:
        if service.pairing == PairingRequirement.Mandatory:
            await pair_protocol(confs[0], service)
        else:
            print(f"Protocol {service.protocol.name} does not require pairing")


asyncio.run(main())  # asyncio.run requires python 3.7+
