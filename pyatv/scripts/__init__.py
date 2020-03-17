"""Scripts bundled with pyatv."""

import json
import argparse
from ipaddress import ip_address

from pyatv import const


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
class TransformScanHosts(argparse.Action):
    """Transform scan hosts into array."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Split hosts and save as array."""
        ips = [ip_address(ip) for ip in values.split(",")]
        setattr(namespace, self.dest, ips)


# pylint: disable=too-few-public-methods
class TransformOutput(argparse.Action):
    """Transform output format to function."""

    def __call__(self, parser, namespace, values, option_string=None):
        """Match protocol string and save correct version."""
        if values == "json":
            setattr(namespace, self.dest, json.dumps)
        else:
            raise argparse.ArgumentTypeError("Valid formats are: json")
