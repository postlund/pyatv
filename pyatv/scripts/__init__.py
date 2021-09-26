"""Scripts bundled with pyatv."""

import argparse
from ipaddress import ip_address
import json
import logging

from pyatv import const

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class TransformProtocol(argparse.Action):
    """Transform protocol in string format to internal representation."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Match protocol string and save correct version."""
        protocols = {proto.name.lower(): proto for proto in const.Protocol}
        if values in protocols:
            setattr(namespace, self.dest, protocols[values])
        else:
            raise argparse.ArgumentTypeError(
                "Valid protocols are: " + ", ".join(protocols.keys())
            )


# pylint: disable=too-few-public-methods
class VerifyScanHosts(argparse.Action):
    """Transform scan hosts into array."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Split hosts and save as array."""
        ip_split = values.split(",")

        # Simple verification that IP addresses has correct format
        [ip_address(ip) for ip in ip_split]  # pylint: disable=expression-not-assigned

        setattr(namespace, self.dest, ip_split)


# pylint: disable=too-few-public-methods
class VerifyScanProtocols(argparse.Action):
    """Transform scan protocols into an array."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Split protocols and save as array."""
        protocols = {proto.name.lower(): proto for proto in const.Protocol}

        parsed_protocols = set()
        for protocol in values.split(","):
            if protocol in protocols:
                parsed_protocols.add(protocols[protocol])
            else:
                raise argparse.ArgumentTypeError(
                    "Valid protocols are: " + ", ".join(protocols.keys())
                )
        setattr(namespace, self.dest, parsed_protocols)


# pylint: disable=too-few-public-methods
class TransformOutput(argparse.Action):
    """Transform output format to function."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Match protocol string and save correct version."""
        if values == "json":
            setattr(namespace, self.dest, json.dumps)
        else:
            raise argparse.ArgumentTypeError("Valid formats are: json")


# pylint: disable=too-few-public-methods
class TransformIdentifiers(argparse.Action):
    """Transform identifiers into array if multiple."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Split identifiers and save as array if more than one."""
        identifiers_split = values.split(",")

        if len(identifiers_split) == 1:
            setattr(namespace, self.dest, values)
        else:
            setattr(namespace, self.dest, set(identifiers_split))
