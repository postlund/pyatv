"""Scripts bundled with pyatv."""

import json
import socket
import logging
import argparse
from ipaddress import ip_address

from aiozeroconf import ServiceInfo

from pyatv import const

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class TransformProtocol(argparse.Action):
    """Transform protocol in string format to internal representation."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Match protocol string and save correct version."""
        if values == "mrp":
            setattr(namespace, self.dest, const.Protocol.MRP)
        elif values == "dmap":
            setattr(namespace, self.dest, const.Protocol.DMAP)
        elif values == "airplay":
            setattr(namespace, self.dest, const.Protocol.AirPlay)
        else:
            raise argparse.ArgumentTypeError("Valid protocols are: mrp, dmap, airplay")


# pylint: disable=too-few-public-methods
class VerifyScanHosts(argparse.Action):
    """Transform scan hosts into array."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Split hosts and save as array."""
        ip_split = values.split(",")
        [ip_address(ip) for ip in ip_split]
        setattr(namespace, self.dest, ip_split)


# pylint: disable=too-few-public-methods
class TransformOutput(argparse.Action):
    """Transform output format to function."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Match protocol string and save correct version."""
        if values == "json":
            setattr(namespace, self.dest, json.dumps)
        else:
            raise argparse.ArgumentTypeError("Valid formats are: json")


async def publish_service(zconf, service, name, address, port, props):
    """Publish a custom zeroconf service."""
    service = ServiceInfo(
        service,
        name + "." + service,
        address=socket.inet_aton(address),
        port=port,
        weight=0,
        priority=0,
        properties=props,
    )

    await zconf.register_service(service)
    _LOGGER.debug("Published zeroconf service: %s", service)

    return service
