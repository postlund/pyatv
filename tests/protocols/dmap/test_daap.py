"""Unit tests for pyatv.protocols.dmap.daap."""

import pytest

from pyatv import exceptions
from pyatv.const import DeviceState, MediaType
from pyatv.protocols.dmap.daap import media_kind, ms_to_s, playstate

# These are extracted from iTunes, see for instance:
# http://www.blooming.no/wp-content/uploads/2013/03/ITLibMediaItem.h
# and also this:
# https://github.com/melloware/dacp-net/blob/master/Melloware.DACP/DACPResponse.cs
# Key: cmst.cmmk
MEDIA_KIND_UNKNOWN = 1
MEDIA_KIND_UNKNOWN2 = 32770  # Reported in #182
MEDIA_KIND_SONG = 2
MEDIA_KIND_MOVIE = 3
MEDIA_KIND_PODCAST = 4
MEDIA_KIND_AUDIOBOOK = 5
MEDIA_KIND_PDFBOOKLET = 6
MEDIA_KIND_MUSICVIDEO = 7
MEDIA_KIND_TVSHOW = 8
MEDIA_KIND_INTERACTIVEBOOKLET = 9
MEDIA_KIND_COACHEDAUDIO = 10
MEDIA_KIND_VIDEOPASS = 11
MEDIA_KIND_HOMEVIDEO = 12
MEDIA_KIND_FUTUREVIDEO = 13
MEDIA_KIND_RINGTONE = 14
MEDIA_KIND_DIGITALBOOKLET = 15
MEDIA_KIND_IOSAPPLICATION = 16
MEDIA_KIND_VOICEMEMO = 17
MEDIA_KIND_ITUNESU = 18
MEDIA_KIND_BOOK = 19
MEDIA_KIND_PDFBOOK = 20
MEDIA_KIND_ALERTTONE = 21
MEDIA_KIND_MUSICVIDEO2 = 32
MEDIA_KIND_PODCAST2 = 36
MEDIA_KIND_TVSHOW2 = 64

# Found on various places on the Internet as well as by testing
# Key: cmst.caps
PLAY_STATE_IDLE = 0
PLAY_STATE_LOADING = 1  # E.g. buffering
PLAY_STATE_STOPPED = 2
PLAY_STATE_PAUSED = 3
PLAY_STATE_PLAYING = 4
PLAY_STATE_FORWARD = 5
PLAY_STATE_BACKWARD = 6


# MEDIA KIND TESTS


def test_unknown_media_kind():
    assert MediaType.Unknown == media_kind(MEDIA_KIND_UNKNOWN)
    assert MediaType.Unknown == media_kind(MEDIA_KIND_UNKNOWN2)


def test_video_media_kinds():
    assert MediaType.Video == media_kind(MEDIA_KIND_MOVIE)
    assert MediaType.Video == media_kind(MEDIA_KIND_MUSICVIDEO)
    assert MediaType.Video == media_kind(MEDIA_KIND_MUSICVIDEO2)
    assert MediaType.Video == media_kind(MEDIA_KIND_VIDEOPASS)
    assert MediaType.Video == media_kind(MEDIA_KIND_HOMEVIDEO)
    assert MediaType.Video == media_kind(MEDIA_KIND_FUTUREVIDEO)
    assert MediaType.Video == media_kind(MEDIA_KIND_ITUNESU)


def test_music_media_kinds():
    assert MediaType.Music == media_kind(MEDIA_KIND_SONG)
    assert MediaType.Music == media_kind(MEDIA_KIND_PODCAST)
    assert MediaType.Music == media_kind(MEDIA_KIND_PODCAST2)
    assert MediaType.Music == media_kind(MEDIA_KIND_COACHEDAUDIO)
    assert MediaType.Music == media_kind(MEDIA_KIND_RINGTONE)
    assert MediaType.Music == media_kind(MEDIA_KIND_VOICEMEMO)
    assert MediaType.Music == media_kind(MEDIA_KIND_ALERTTONE)


def test_tv_kinds():
    assert MediaType.TV == media_kind(MEDIA_KIND_TVSHOW)
    assert MediaType.TV == media_kind(MEDIA_KIND_TVSHOW2)


def test_unknown_media_kind_throws():
    with pytest.raises(exceptions.UnknownMediaKindError):
        media_kind(99999)


# PLAYSTATE TESTS


def test_device_state_no_media():
    # This test should not really be here as "None" is in reality not a
    # valid value. But it is supported nonetheless because that makes
    # usage nicer. None means that the field is not included in a
    # server response, which matches the behavior of dmap.first.
    assert DeviceState.Idle == playstate(None)


def test_regular_playstates():
    assert DeviceState.Idle == playstate(PLAY_STATE_IDLE)
    assert DeviceState.Loading == playstate(PLAY_STATE_LOADING)
    assert DeviceState.Stopped == playstate(PLAY_STATE_STOPPED)
    assert DeviceState.Paused == playstate(PLAY_STATE_PAUSED)
    assert DeviceState.Playing == playstate(PLAY_STATE_PLAYING)
    assert DeviceState.Seeking == playstate(PLAY_STATE_FORWARD)
    assert DeviceState.Seeking == playstate(PLAY_STATE_BACKWARD)


def test_unknown_playstate_throws():
    with pytest.raises(exceptions.UnknownPlayStateError):
        playstate(99999)


# TIME TESTS


def test_no_time_returns_zero():
    assert 0 == ms_to_s(None)


def test_time_in_seconds():
    assert 0 == ms_to_s(400)
    assert 1 == ms_to_s(501)
    assert 36 == ms_to_s(36000)


def test_invalid_time():
    # Sometimes really large times are reported during buffering == this test
    # handles those special cases.
    assert 0 == ms_to_s(2**32 - 1)
