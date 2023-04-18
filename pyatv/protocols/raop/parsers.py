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


class MetadataType(IntFlag):
    """Metadata types supported by receiver."""

    NotSupported = 0
    Text = 1
    Artwork = 2
    Progress = 4


# pylint: enable=invalid-name


def get_audio_properties(properties: Mapping[str, str]) -> Tuple[int, int, int]:
    """Parse Zeroconf properties and return sample rate, channels and sample size."""
    try:
        sample_rate = int(properties.get("sr", DEFAULT_SAMPLE_RATE))
        channels = int(properties.get("ch", DEAFULT_CHANNELS))
        sample_size = int(int(properties.get("ss", DEFAULT_SAMPLE_SIZE)) / 8)
    except Exception as ex:
        raise exceptions.ProtocolError("invalid audio property") from ex
    return sample_rate, channels, sample_size


def get_encryption_types(properties: Mapping[str, str]) -> EncryptionType:
    """Return encryption types supported by receiver.

    Input format from zeroconf is a comma separated list:

        et=0,1,3

    0=unencrypted, 1=RSA, 3=FairPlay, 4=MFiSAP, 5=FairPlay SAPv2.5
    """
    output = EncryptionType.Unknown
    try:
        enc_types = [int(x) for x in properties["et"].split(",")]
    except (KeyError, ValueError):
        return output

    for enc_type in enc_types:
        output |= {
            0: EncryptionType.Unencrypted,
            1: EncryptionType.RSA,
            3: EncryptionType.FairPlay,
            4: EncryptionType.MFiSAP,
            5: EncryptionType.FairPlaySAPv25,
        }.get(enc_type, EncryptionType.Unknown)
    return output


def get_metadata_types(properties: Mapping[str, str]) -> MetadataType:
    """Return metadata types supported by receiver.

    Input format from zeroconf is comma separated list:

        md=0,1,2

    0=text, 1=artwork, 2=progress
    """
    output = MetadataType.NotSupported
    try:
        md_types = [int(x) for x in properties["md"].split(",")]
    except (KeyError, ValueError):
        return output

    for md_type in md_types:
        output |= {
            0: MetadataType.Text,
            1: MetadataType.Artwork,
            2: MetadataType.Progress,
        }.get(md_type, MetadataType.NotSupported)
    return output
