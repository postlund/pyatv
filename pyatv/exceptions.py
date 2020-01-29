"""Local exceptions used by library."""


class NoServiceError(Exception):
    """Thrown when connecting to a device with no usable service."""


class UnsupportedProtocolError(Exception):
    """Thrown when an unsupported protocol was requested."""


class ConnectionFailedError(Exception):
    """Thrown when connection fails, e.g. refused or timed out."""


class PairingError(Exception):
    """Thrown when pairing fails."""


class AuthenticationError(Exception):
    """Thrown when authentication fails."""


class NotSupportedError(NotImplementedError):
    """Thrown when trying to perform an action that is not supported."""


class InvalidDmapDataError(Exception):
    """Thrown when invalid DMAP data is parsed."""


class UnknownMediaKindError(Exception):
    """Thrown when an unknown media kind is found."""


class UnknownPlayStateError(Exception):
    """Thrown when an unknown play state is found."""


class NoAsyncListenerError(Exception):
    """Thrown when starting AsyncUpdater with no listener."""


class NoCredentialsError(Exception):
    """Thrown if credentials are missing."""


class InvalidCredentialsError(Exception):
    """Thrown if credentials are invalid."""


class DeviceIdMissingError(Exception):
    """Thrown when device id is missing."""


class BackOffError(Exception):
    """Thrown when device mandates a backoff period."""


class PlaybackError(Exception):
    """Thrown when media playback failed."""
