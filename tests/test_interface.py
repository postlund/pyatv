"""Unit tests for pyatv.interface."""

import unittest

from pyatv import (const, convert, interface)


class TestClass:

    variable = 1234

    def test_method(self):
        """Help text."""
        pass

    def another_method(self):
        """Some other help text. More text here. Test."""
        pass

    @property
    def some_property(self):
        """Property help"""
        pass

    def dev_method(self):
        """Developer help."""
        pass

    def abbrev_help(self):
        """Type, e.g. a, b or c."""
        pass

    def abbrev_help_more_text(self):
        """Type, e.g. a, b or c. Some other text."""
        pass

    def _private_method_ignored(self):
        """Not parsed."""
        pass


class PlayingDummy(interface.Playing):

    def __init__(self, media_type=const.MEDIA_TYPE_VIDEO,
                 play_state=const.PLAY_STATE_PLAYING, title=None, artist=None,
                 album=None, total_time=None, position=None):
        self._media_type = media_type
        self._play_state = play_state
        self._title = title
        self._artist = artist
        self._album = album
        self._total_time = total_time
        self._position = position

    @property
    def media_type(self):
        """What type of media is currently playing, e.g. video, music."""
        return self._media_type

    @property
    def play_state(self):
        """Current play state, e.g. playing or paused."""
        return self._play_state

    @property
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        return self._title

    @property
    def artist(self):
        """Artist of the currently playing song."""
        return self._artist

    @property
    def album(self):
        """Album of the currently playing song."""
        return self._album

    @property
    def total_time(self):
        """Total play time in seconds."""
        return self._total_time

    @property
    def position(self):
        """Current position in the playing media (seconds)."""
        return self._position


class InterfaceTest(unittest.TestCase):

    def setUp(self):
        self.obj = TestClass()
        self.methods = interface.retrieve_commands(self.obj)

    # COMMANDS AND HELP TEXT

    def test_get_commands(self):
        self.assertEqual(5, len(self.methods))
        self.assertTrue('test_method' in self.methods)
        self.assertTrue('another_method' in self.methods)
        self.assertTrue('some_property' in self.methods)
        self.assertTrue('abbrev_help' in self.methods)

    def test_get_developer_command(self):
        methods = interface.retrieve_commands(self.obj, developer=True)
        self.assertEqual(6, len(methods))
        self.assertEqual('Developer help', methods['dev_method'])

    def test_get_first_sentence_without_leading_period_in_pydoc(self):
        self.assertEqual('Help text', self.methods['test_method'])
        self.assertEqual(
            'Some other help text', self.methods['another_method'])
        self.assertEqual('Property help', self.methods['some_property'])

    def test_try_to_be_smart_with_abbreviations(self):
        self.assertEqual(
            'Type, e.g. a, b or c', self.methods['abbrev_help'])
        self.assertEqual(
            'Type, e.g. a, b or c', self.methods['abbrev_help_more_text'])

    # PLAYING STR

    def test_playing_media_type_and_playstate(self):
        out = str(PlayingDummy())
        self.assertIn(convert.media_type_str(const.MEDIA_TYPE_VIDEO), out)
        self.assertIn(convert.playstate_str(const.PLAY_STATE_PLAYING), out)

    def test_playing_title_artist_album(self):
        out = str(PlayingDummy(
            title='mytitle', artist='myartist', album='myalbum'))
        self.assertIn('mytitle', out)
        self.assertIn('myartist', out)
        self.assertIn('myalbum', out)

    def test_playing_only_position(self):
        self.assertIn('1234', str(PlayingDummy(position=1234)))

    def test_playing_only_total_time(self):
        self.assertIn('5678', str(PlayingDummy(total_time=5678)))

    def test_playing_both_position_and_total_time(self):
        out = str(PlayingDummy(position=1234, total_time=5678))
        self.assertIn('1234/5678', out)
