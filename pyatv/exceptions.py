"""Local exceptions used by library."""


class AuthenticationError(Exception):
    """Thrown when login fails."""

    pass


class NotSupportedError(NotImplementedError):
    """Thrown when trying to perform an action that is not supported."""

    pass


class InvalidDmapDataError(Exception):
    """Thrown when invalid DMAP data is parsed."""

    pass


class UnknownServerResponseError(Exception):
    """Thrown when somethins unknown is send back from the Apple TV."""

    pass


class UnknownMediaKind(Exception):
    """Thrown when an unknown media kind is found."""

    pass


class UnknownPlayState(Exception):
    """Thrown when an unknown play state is found."""

    pass


class NoAsyncListenerError(Exception):
    """Thrown when starting AsyncUpdater with no listener."""

    pass


class AsyncUpdaterRunningError(Exception):
    """Thrown when performing an invalid action in AsyncUpdater.."""

    pass


class NoCredentialsError(Exception):
    """Thrown if performing an action before initialize is called."""

    pass


class DeviceAuthenticationError(Exception):
    """Thrown when device authentication fails."""

    pass
