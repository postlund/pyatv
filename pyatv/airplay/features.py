"""Manage announced AirPlay features."""
from enum import IntFlag
import re

# pylint: disable=invalid-name


class AirPlayFeatures(IntFlag):
    """Features supported by AirPlay."""

    SupportsAirPlayVideoV1 = 1 << 0
    SupportsAirPlayPhoto = 1 << 1
    SupportsAirPlaySlideShow = 1 << 5
    SupportsAirPlayScreen = 1 << 7
    SupportsAirPlayAudio = 1 << 9
    AudioRedundant = 1 << 11
    Authentication_4 = 1 << 14
    MetadataFeatures_0 = 1 << 15
    MetadataFeatures_1 = 1 << 16
    MetadataFeatures_2 = 1 << 17
    AudioFormats_0 = 1 << 18
    AudioFormats_1 = 1 << 19
    AudioFormats_2 = 1 << 20
    AudioFormats_3 = 1 << 21
    Authentication_1 = 1 << 23
    Authentication_8 = 1 << 26
    SupportsLegacyPairing = 1 << 27
    HasUnifiedAdvertiserInfo = 1 << 30
    IsCarPlay = 1 << 32  # SupportsVolume?
    SupportsAirPlayVideoPlayQueue = 1 << 33
    SupportsAirPlayFromCloud = 1 << 34
    SupportsTLS_PSK = 1 << 35
    SupportsUnifiedMediaControl = 1 << 38
    SupportsBufferedAudio = 1 << 40
    SupportsPTP = 1 << 41
    SupportsScreenMultiCodec = 1 << 42
    SupportsSystemPairing = 1 << 43
    IsAPValeriaScreenSender = 1 << 44
    SupportsHKPairingAndAccessControl = 1 << 46
    SupportsCoreUtilsPairingAndEncryption = 1 << 48
    SupportsAirPlayVideoV2 = 1 << 49
    MetadataFeatures_3 = 1 << 50
    SupportsUnifiedPairSetupandMFi = 1 << 51
    SupportsSetPeersExtendedMessage = 1 << 52
    SupportsAPSync = 1 << 54
    SupportsWoL = 1 << 55
    SupportsWoL2 = 1 << 56
    SupportsHangdogRemoteControl = 1 << 58
    SupportsAudioStreamConnectionSetup = 1 << 59
    SupportsAudioMetadataControl = 1 << 60
    SupportsRFC2198Redundancy = 1 << 61


# pylint: enable=invalid-name


def parse(features: str) -> AirPlayFeatures:
    """Parse an AirPlay feature string and return what is supported.

    A feature string have one of the following formats:
      - 0x12345678
      - 0x12345678,0xabcdef12 => 0xabcdef1212345678
    """
    match = re.match(r"^0x([0-9A-Fa-f]{1,8})(?:,0x([0-9A-Fa-f]{1,8})|)$", features)
    if match is None:
        raise ValueError(f"invalid feature string: {features}")

    value, upper = match.groups()
    if upper is not None:
        value = upper + value
    return AirPlayFeatures(int(value, 16))
