"""Unit tests for pyatv.types."""

import unittest

from pyatv import (const, convert, exceptions)

# These are extracted from iTunes, see for instance:
# http://www.blooming.no/wp-content/uploads/2013/03/ITLibMediaItem.h
# Key: cmst.cmmk
MEDIA_KIND_UNKNOWN = 1
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


# Found on various places on the Internet as well as by testing
# Key: cmst.caps
PLAY_STATE_LOADING = 1  # E.g. buffering
PLAY_STATE_PAUSED = 3
PLAY_STATE_PLAYING = 4
PLAY_STATE_FORWARD = 5
PLAY_STATE_BACKWARD = 6


class TagsTest(unittest.TestCase):

    # MEDIA KIND TESTS

    def test_unknown_media_kind(self):
        self.assertEqual(const.MEDIA_TYPE_UNKNOWN,
                         convert.media_kind(MEDIA_KIND_UNKNOWN))

    def test_video_media_kinds(self):
        self.assertEqual(const.MEDIA_TYPE_VIDEO,
                         convert.media_kind(MEDIA_KIND_MOVIE))
        self.assertEqual(const.MEDIA_TYPE_VIDEO,
                         convert.media_kind(MEDIA_KIND_MUSICVIDEO))
        self.assertEqual(const.MEDIA_TYPE_VIDEO,
                         convert.media_kind(MEDIA_KIND_VIDEOPASS))
        self.assertEqual(const.MEDIA_TYPE_VIDEO,
                         convert.media_kind(MEDIA_KIND_HOMEVIDEO))
        self.assertEqual(const.MEDIA_TYPE_VIDEO,
                         convert.media_kind(MEDIA_KIND_FUTUREVIDEO))
        self.assertEqual(const.MEDIA_TYPE_VIDEO,
                         convert.media_kind(MEDIA_KIND_ITUNESU))

    def test_music_media_kinds(self):
        self.assertEqual(const.MEDIA_TYPE_MUSIC,
                         convert.media_kind(MEDIA_KIND_SONG))
        self.assertEqual(const.MEDIA_TYPE_MUSIC,
                         convert.media_kind(MEDIA_KIND_PODCAST))
        self.assertEqual(const.MEDIA_TYPE_MUSIC,
                         convert.media_kind(MEDIA_KIND_COACHEDAUDIO))
        self.assertEqual(const.MEDIA_TYPE_MUSIC,
                         convert.media_kind(MEDIA_KIND_RINGTONE))
        self.assertEqual(const.MEDIA_TYPE_MUSIC,
                         convert.media_kind(MEDIA_KIND_VOICEMEMO))
        self.assertEqual(const.MEDIA_TYPE_MUSIC,
                         convert.media_kind(MEDIA_KIND_ALERTTONE))

    def test_tv_kinds(self):
        self.assertEqual(const.MEDIA_TYPE_TV,
                         convert.media_kind(MEDIA_KIND_TVSHOW))

    def test_unknown_media_kind_throws(self):
        with self.assertRaises(exceptions.UnknownMediaKind):
            convert.media_kind(99999)

    # PLAYSTATE TESTS

    def test_play_state_no_media(self):
        # This test should not really be here as "None" is in reality not a
        # valid value. But it is supported nonetheless because that makes
        # usage nicer. None means that the field is not included in a
        # server response, which matches the behavior of dmap.first.
        self.assertEqual(const.PLAY_STATE_NO_MEDIA,
                         convert.playstate(None))

    def test_regular_play_states(self):
        self.assertEqual(const.PLAY_STATE_LOADING,
                         convert.playstate(PLAY_STATE_LOADING))
        self.assertEqual(const.PLAY_STATE_PAUSED,
                         convert.playstate(PLAY_STATE_PAUSED))
        self.assertEqual(const.PLAY_STATE_PLAYING,
                         convert.playstate(PLAY_STATE_PLAYING))
        self.assertEqual(const.PLAY_STATE_FAST_FORWARD,
                         convert.playstate(PLAY_STATE_FORWARD))
        self.assertEqual(const.PLAY_STATE_FAST_BACKWARD,
                         convert.playstate(PLAY_STATE_BACKWARD))

    def test_unknown_playstate_throws(self):
        with self.assertRaises(exceptions.UnknownPlayState):
            convert.playstate(99999)

    # TIME TESTS

    def test_no_time_returns_zero(self):
        self.assertEqual(0, convert.ms_to_s(None))

    def test_time_in_seconds(self):
        self.assertEqual(0, convert.ms_to_s(400))
        self.assertEqual(1, convert.ms_to_s(501))
        self.assertEqual(36, convert.ms_to_s(36000))

    def test_invalid_time(self):
        # Sometimes really large times are reported during buffering, this test
        # handles those special cases.
        self.assertEqual(0, convert.ms_to_s(2**32 - 1))
