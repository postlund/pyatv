"""Manage announced AirPlay features."""

from enum import Enum, IntFlag, auto
import logging
import math
import plistlib
import re
from typing import Any, Dict, Mapping, Union

from pyatv.auth.hap_pairing import (
    TRANSIENT_CREDENTIALS,
    AuthenticationType,
    HapCredentials,
)
from pyatv.const import PairingRequirement
from pyatv.core import MutableService
from pyatv.interface import BaseService
from pyatv.settings import AirPlayVersion
from pyatv.support import map_range
from pyatv.support.http import HttpRequest, HttpResponse

# pylint: disable=invalid-name

# Status flags
PIN_REQUIRED = 0x8
PASSWORD_BIT = 0x80
LEGACY_PAIRING_BIT = 0x200

DBFS_MIN = -30.0
DBFS_MAX = 0.0
PERCENTAGE_MIN = 0.0
PERCENTAGE_MAX = 100.0

UNSUPPORTED_MODELS = [r"^Mac\d+,\d+$"]


class AirPlayMajorVersion(Enum):
    """Major AirPlay protocol version."""

    AirPlayV1 = auto()
    AirPlayV2 = auto()


def _get_flags(properties: Mapping[str, str]) -> int:
    # Flags are either present via "sf" or "flags"
    flags = properties.get("sf") or properties.get("flags") or "0x0"
    return int(flags, 16)


# These flags have been imported from here:
# https://emanuelecozzi.net/docs/airplay2/features/
# Should be the same as the ones from here:
# https://openairplay.github.io/airplay-spec/features.html
# But seems to be some inconsistencies. Worth to keep in mind.
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
    - But 0x8 set in sf/flags

    There's an "act" (Access Control Type) field present in some cases. Values are yet
    unknown, but "2" seems to correspond to "Current User".

    Other cases are optimistically treated as NotNeeded.
    """
    if _get_flags(service.properties) & (LEGACY_PAIRING_BIT | PIN_REQUIRED):
        return PairingRequirement.Mandatory

    # "Current User" not supported by pyatv
    if service.properties.get("act", "0") == "2":
        return PairingRequirement.Unsupported
    return PairingRequirement.NotNeeded


# TODO: It is not fully understood how to determine if a device supports remote control
# over AirPlay, so this method makes a pure guess. We know that Apple TVs running tvOS
# X (X>=13?) support it as well as HomePods, something we can identify from the model
# string. This implementation should however be improved when it's properly known how
# to check for support.
def is_remote_control_supported(
    service: BaseService, credentials: HapCredentials
) -> bool:
    """Return if device supports remote control tunneling."""
    model = service.properties.get("model", "")

    # HomePod supports remote control but only with transient credentials
    if model.startswith("AudioAccessory"):
        return credentials == TRANSIENT_CREDENTIALS

    if not model.startswith("AppleTV"):
        return False

    # tvOS must be at least version 13 and HAP credentials are required by Apple TV
    version = service.properties.get("osvers", "0.0").split(".", maxsplit=1)[0]
    return float(version) >= 13.0 and credentials.type == AuthenticationType.HAP


def encode_plist_body(data: Any):
    """Encode a binary plist payload."""
    return plistlib.dumps(
        data,
        fmt=plistlib.FMT_BINARY,  # pylint: disable=no-member
    )


def decode_plist_body(body: Union[str, bytes, Dict[Any, Any]]) -> Any:
    """Decode a binary plist payload."""
    try:
        if isinstance(body, Dict):
            return body
        return plistlib.loads(body if isinstance(body, bytes) else body.encode("utf-8"))
    except plistlib.InvalidFileException:
        return None


def log_request(logger, request: HttpRequest, message_prefix="") -> None:
    """Log an AirPlay request with optional binary plist body."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("%sRequest: %s", message_prefix, request)
    if request.headers.get("content-type") == "application/x-apple-binary-plist" and (
        payload := decode_plist_body(request.body)
    ):
        logger.debug(
            "%s%s request plist content: %s",
            message_prefix,
            request.protocol,
            payload,
        )


def log_response(logger, response: HttpResponse, message_prefix="") -> None:
    """Log an AirPlay response with optional binary plist body."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("%sResponse: %s", message_prefix, response)
    if (
        response
        and response.headers.get("content-type") == "application/x-apple-binary-plist"
        and (payload := decode_plist_body(response.body))
    ):
        logger.debug(
            "%s%s response plist content: %s",
            message_prefix,
            response.protocol,
            payload,
        )


# TODO: I don't know how to properly detect if a receiver support AirPlay 2 or not,
# so I'm guessing until I know better. The basic idea here is simple: the service
# should have the "features" flag (either "features" or "ft") and either bit 38 or
# bit 48 should be present.
def get_protocol_version(
    service: BaseService, preferred_version: AirPlayVersion
) -> AirPlayMajorVersion:
    """Return major AirPlay version supported by a service."""
    if preferred_version == AirPlayVersion.Auto:
        features = service.properties.get("ft")
        if not features:
            features = service.properties.get("features", "0x0")

        parsed_features = parse_features(features)
        if (
            AirPlayFlags.SupportsUnifiedMediaControl in parsed_features
            or AirPlayFlags.SupportsCoreUtilsPairingAndEncryption in parsed_features
        ):
            return AirPlayMajorVersion.AirPlayV2
        return AirPlayMajorVersion.AirPlayV1
    if preferred_version == AirPlayVersion.V2:
        return AirPlayMajorVersion.AirPlayV2
    return AirPlayMajorVersion.AirPlayV1


def update_service_details(service: MutableService):
    """Update AirPlay service according to that it supports."""
    service.requires_password = is_password_required(service)

    if service.properties.get("acl", "0") == "1":
        # Access control might say that pairing is not possible, e.g. only devices
        # belonging to the same home (not supported by pyatv)
        service.pairing = PairingRequirement.Disabled
    elif any(
        re.match(model, service.properties.get("model", ""))
        for model in UNSUPPORTED_MODELS
    ):
        # Set as "unsupported" for devices we know that pyatv does
        # (yet) support.
        service.pairing = PairingRequirement.Unsupported
    else:
        service.pairing = get_pairing_requirement(service)


def pct_to_dbfs(level: float) -> float:
    """Convert percentage level to dBFS.

    Used for volume levels in AirPlay.
    """
    # AirPlay uses -144.0 as muted volume, so re-map 0.0 to that
    if math.isclose(level, 0.0):
        return -144.0

    # Map percentage to dBFS
    return map_range(level, PERCENTAGE_MIN, PERCENTAGE_MAX, DBFS_MIN, DBFS_MAX)


def dbfs_to_pct(level: float) -> float:
    """Convert dBFS to percentage."""
    # AirPlay uses -144.0 as "muted", but we treat everything below -30.0 as
    # muted to be a bit defensive
    if level < DBFS_MIN:
        return PERCENTAGE_MIN

    # Map dBFS to percentage
    return map_range(level, DBFS_MIN, DBFS_MAX, PERCENTAGE_MIN, PERCENTAGE_MAX)
