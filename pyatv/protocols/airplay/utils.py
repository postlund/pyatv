"""Manage announced AirPlay features."""
from enum import IntFlag
import re
from typing import Mapping

from pyatv.const import PairingRequirement
from pyatv.interface import BaseService

# pylint: disable=invalid-name

PASSWORD_BIT = 0x80
LEGACY_PAIRING_BIT = 0x200


def _get_flags(properties: Mapping[str, str]) -> int:
    # Flags are either present via "sf" or "flags"
    flags = properties.get("sf")
    if not flags:
        flags = properties.get("flags")
        if not flags:
            flags = properties.get("ft")
    return int(flags or "0x0", 16)


class AirPlayFlags(IntFlag):
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


def parse_features(features: str) -> AirPlayFlags:
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
    return AirPlayFlags(int(value, 16))


def is_password_required(service: BaseService) -> bool:
    """Return if password is required by AirPlay service.

    A password is required under these conditions:
    - "pw" is true
    - "sf", "ft" or "flags" has bit 0x80 set
    """
    # "pw" flag
    if service.properties.get("pw", "false").lower() == "true":
        return True

    # Legacy "flags" property
    if _get_flags(service.properties) & PASSWORD_BIT:
        return True

    return False


def get_pairing_requirement(service: BaseService) -> PairingRequirement:
    """Return pairing requirement for service.

    Pairing requirement is Mandatory if:
    - Bit 0x200 is set in sf (AirPlay v1)/flags (AirPlay v2)
    - SupportsLegacyPairing or SupportsCoreUtilsPairingAndEncryption set in features

    Other cases are optimistically treated as NotNeeded.
    """
    # Legacy "flags" property
    if _get_flags(service.properties) & LEGACY_PAIRING_BIT:
        return PairingRequirement.Mandatory

    # Feature flag in AirPlay v2
    feature_flags = parse_features(service.properties.get("features", "0x0"))
    if feature_flags & (
        AirPlayFlags.SupportsLegacyPairing
        | AirPlayFlags.SupportsCoreUtilsPairingAndEncryption
    ):
        return PairingRequirement.Mandatory

    return PairingRequirement.NotNeeded


# TODO: It is not fully understood how to determine if a device supports remote control
# over AirPlay, so this method makes a pure guess. We know that Apple TVs running tvOS
# X (X>=13?) support it as well as HomePods, something we can identify from the model
# string. This implementation should however be improved when it's properly known how
# to check for support.
def is_remote_control_supported(service: BaseService) -> bool:
    """Return if device supports remote control tunneling."""
    model = service.properties.get("model", "")
    if model.startswith("AudioAccessory"):
        return True

    if not model.startswith("AppleTV"):
        return False

    version = service.properties.get("osvers", "0.0").split(".", maxsplit=1)[0]
    return float(version) >= 13.0
