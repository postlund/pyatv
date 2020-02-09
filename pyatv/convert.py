"""Various types of extraction and conversion functions."""

from pyatv import exceptions
from pyatv.const import (
    Protocol, MediaType, DeviceState, RepeatState, ShuffleState)


def media_kind(kind):
    """Convert iTunes media kind to API representation."""
    if kind in [1, 32770]:
        return MediaType.Unknown
    if kind in [3, 7, 11, 12, 13, 18, 32]:
        return MediaType.Video
    if kind in [2, 4, 10, 14, 17, 21, 36]:
        return MediaType.Music
    if kind in [8, 64]:
        return MediaType.TV

    raise exceptions.UnknownMediaKindError('Unknown media kind: ' + str(kind))


def media_type_str(mediatype):
    """Convert internal API media type to string."""
    if mediatype == MediaType.Unknown:
        return 'Unknown'
    if mediatype == MediaType.Video:
        return 'Video'
    if mediatype == MediaType.Music:
        return 'Music'
    if mediatype == MediaType.TV:
        return 'TV'
    return 'Unsupported'


def playstate(state):
    """Convert iTunes playstate to API representation."""
    # pylint: disable=too-many-return-statements
    if state == 0 or state is None:
        return DeviceState.Idle
    if state == 1:
        return DeviceState.Loading
    if state == 2:
        return DeviceState.Stopped
    if state == 3:
        return DeviceState.Paused
    if state == 4:
        return DeviceState.Playing
    if state in (5, 6):
        return DeviceState.Seeking

    raise exceptions.UnknownPlayStateError('Unknown playstate: ' + str(state))


# pylint: disable=too-many-return-statements
def playstate_str(state):
    """Convert internal API playstate to string."""
    if state == DeviceState.Idle:
        return 'Idle'
    if state == DeviceState.Loading:
        return 'Loading'
    if state == DeviceState.Stopped:
        return 'Stopped'
    if state == DeviceState.Paused:
        return 'Paused'
    if state == DeviceState.Playing:
        return 'Playing'
    if state == DeviceState.Seeking:
        return 'Seeking'

    return 'Unsupported'


def repeat_str(state):
    """Convert internal API repeat state to string."""
    if state == RepeatState.Off:
        return 'Off'
    if state == RepeatState.Track:
        return 'Track'
    if state == RepeatState.All:
        return 'All'
    return 'Unsupported'


def shuffle_str(state):
    """Convert internal API shuffle state to string."""
    if state == ShuffleState.Off:
        return 'Off'
    if state == ShuffleState.Albums:
        return 'Albums'
    if state == ShuffleState.Songs:
        return 'Songs'
    return 'Unsupported'


def ms_to_s(time):
    """Convert time in ms to seconds."""
    if time is None:
        return 0

    # Happens in some special cases, just return 0
    if time >= (2**32 - 1):
        return 0
    return round(time / 1000.0)


def protocol_str(protocol):
    """Convert internal API protocol to string."""
    if protocol == Protocol.MRP:
        return 'MRP'
    if protocol == Protocol.DMAP:
        return 'DMAP'
    if protocol == Protocol.AirPlay:
        return 'AirPlay'
    return 'Unknown'
