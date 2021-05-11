"""Utility methods for parsing various kinds of data."""

from enum import IntFlag
from typing import Mapping, Tuple

from pyatv import exceptions

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_SAMPLE_SIZE = 16  # bits
DEAFULT_CHANNELS = 2

# pylint: disable=invalid-name


class EncryptionType(IntFlag):
    """Encryptions supported by receiver."""

    Unknown = 0
    Unencrypted = 1
    RSA = 2
    FairPlay = 4
    MFiSAP = 8
    FairPlaySAPv25 = 16


# pylint: enable=invalid-name


def get_audio_properties(properties: Mapping[str, str]) -> Tuple[int, int, int]:
    """Parse Zeroconf properties and return sample rate, channels and sample size."""
    try:
        sample_rate = int(properties.get("sr", DEFAULT_SAMPLE_RATE))
        channels = int(properties.get("ch", DEAFULT_CHANNELS))
        sample_size = int(int(properties.get("ss", DEFAULT_SAMPLE_SIZE)) / 8)
    except Exception as ex:
        raise exceptions.ProtocolError("invalid audio property") from ex
    else:
        return sample_rate, channels, sample_size


def get_encryption_types(properties: Mapping[str, str]) -> EncryptionType:
    """Return encryption types supported by receiver.

    Input format from zeroconf is a comma separated list:

        0,1,3

    Each number represents one encryption type.
    """
    output = EncryptionType.Unknown
    try:
        enc_types = [int(x) for x in properties["et"].split(",")]
    except (KeyError, ValueError):
        return output

    else:
        for enc_type in enc_types:
            output |= {
                0: EncryptionType.Unencrypted,
                1: EncryptionType.RSA,
                3: EncryptionType.FairPlay,
                4: EncryptionType.MFiSAP,
                5: EncryptionType.FairPlaySAPv25,
            }.get(enc_type, EncryptionType.Unknown)
    return output
