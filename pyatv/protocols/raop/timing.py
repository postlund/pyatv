"""Methods for working with time and synchronization in RAOP.

The timing routines in this module is based on the excellent work of RAOP-Player:
https://github.com/philippe44/RAOP-Player
"""

from time import perf_counter
from typing import Tuple


# TODO: Replace with time.perf_counter_ns when python 3.6 is dropped
def perf_counter_ns():
    """Return a perf_counter time in nanoseconds."""
    return int(perf_counter() * 10 ** 9)


def ntp_now() -> int:
    """Return current time in NTP format."""
    now_us = perf_counter_ns() / 1000
    seconds = int(now_us / 1000000)
    frac = int(now_us - seconds * 1000000)
    return (seconds + 0x83AA7E80) << 32 | (int((frac << 32) / 1000000))


def ntp2parts(ntp: int) -> Tuple[int, int]:
    """Split NTP time into seconds and fraction."""
    return ntp >> 32, ntp & 0xFFFFFFFF


def ntp2ts(ntp: int, rate: int) -> int:
    """Comvert NTP time into timestamp."""
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
