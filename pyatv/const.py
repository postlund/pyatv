"""Constants used in the public API."""

MAJOR_VERSION = 0
MINOR_VERSION = 3
PATCH_VERSION = 2
__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)

# Corresponds to "mediakind", cmst.cmmk, in iTunes (but more coerced here)

#: Media type is unknown
MEDIA_TYPE_UNKNOWN = 1

#: Media type is video
MEDIA_TYPE_VIDEO = 2

#: Media type is music
MEDIA_TYPE_MUSIC = 3

#: Media type is TV
MEDIA_TYPE_TV = 4


# Corresponds to "playstate", cmst.playkind, in iTunes (still not fully known)

#: No media is currently select/playing
PLAY_STATE_NO_MEDIA = 1

#: Media is loading/buffering
PLAY_STATE_LOADING = 2

#: Media is paused
PLAY_STATE_PAUSED = 3

#: Media is playing
PLAY_STATE_PLAYING = 4

#: Media is being fast forwarded
PLAY_STATE_FAST_FORWARD = 5

#: Media is being rewinded
PLAY_STATE_FAST_BACKWARD = 6


# Corresponds to "repeatstate", dacp.repeatstate, in iTunes

#: No repeat
REPEAT_STATE_OFF = 0

#: Repeat current track
REPEAT_STATE_TRACK = 1

#: Repeat all tracks
REPEAT_STATE_ALL = 2
