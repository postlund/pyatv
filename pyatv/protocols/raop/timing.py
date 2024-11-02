"""Methods for working with time and synchronization in RAOP.

The timing routines in this module is based on the excellent work of RAOP-Player:
https://github.com/philippe44/RAOP-Player
"""

from time import time_ns
from typing import Tuple


def ntp_now() -> int:
    """Return current time in NTP format."""
    now_us = time_ns() / 1000
    seconds = int(now_us / 1000000)
    frac = int(now_us - seconds * 1000000)
    return (seconds + 0x83AA7E80) << 32 | (int((frac << 32) / 1000000))


def ntp2parts(ntp: int) -> Tuple[int, int]:
    """Split NTP time into seconds and fraction."""
    return ntp >> 32, ntp & 0xFFFFFFFF


def ntp2ts(ntp: int, rate: int) -> int:
    """Convert NTP time into timestamp."""
    return int((ntp >> 16) * rate) >> 16


def ts2ntp(timestamp: int, rate: int) -> int:
    """Convert timestamp into NTP time."""
    return int(int(timestamp << 16) / rate) << 16


def ntp2ms(ntp: int) -> int:
    """Convert NTP time to milliseconds."""
    return ((ntp >> 10) * 1000) >> 22


def ts2ms(timestamp: int, rate: int) -> int:
    """Convert timestamp to milliseconds."""
    return ntp2ms(ts2ntp(timestamp, rate))
