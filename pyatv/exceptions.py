"""Local exceptions used by library."""


class NoServiceError(Exception):
    """Thrown when connecting to a device with no usable service."""


class UnsupportedProtocolError(Exception):
    """Thrown when an unsupported protocol was requested."""


class AuthenticationError(Exception):
    """Thrown when login fails."""


class NotSupportedError(NotImplementedError):
    """Thrown when trying to perform an action that is not supported."""


class InvalidDmapDataError(Exception):
    """Thrown when invalid DMAP data is parsed."""


class UnknownServerResponseError(Exception):
    """Thrown when somethins unknown is send back from the Apple TV."""


class UnknownMediaKind(Exception):
    """Thrown when an unknown media kind is found."""


class UnknownPlayState(Exception):
    """Thrown when an unknown play state is found."""


class NoAsyncListenerError(Exception):
    """Thrown when starting AsyncUpdater with no listener."""


class AsyncUpdaterRunningError(Exception):
    """Thrown when performing an invalid action in AsyncUpdater.."""


class NoCredentialsError(Exception):
    """Thrown if performing an action before initialize is called."""


class DeviceAuthenticationError(Exception):
    """Thrown when device authentication fails."""


class DeviceIdMissingError(Exception):
    """Thrown when device id is missing."""


class BackOffError(Exception):
    """Thrown when device mandates a backoff period."""
