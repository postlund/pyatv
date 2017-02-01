"""Functional tests using the API with a fake Apple TV."""

from tests.log_output_handler import LogOutputHandler
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import (AppleTVDevice, connect_to_apple_tv, const, exceptions)
from tests.fake_apple_tv import (FakeAppleTV, AppleTVUseCases)


HSGID = '12345-6789-0'
SESSION_ID = 55555


class FunctionalTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.atv = self.get_connected_device()
        self.log_handler = LogOutputHandler(self)

    def tearDown(self):
        AioHTTPTestCase.tearDown(self)
        self.log_handler.tearDown()

    def get_app(self, loop):
        self.fake_atv = FakeAppleTV(loop, HSGID, SESSION_ID, self)
        self.usecase = AppleTVUseCases(self.fake_atv)

        # Import TestServer here and not globally, otherwise py.test will
        # complain when running:
        #
        #   test_functional.py cannot collect test class 'TestServer'
        #   because it has a __init__ constructor
        from aiohttp.test_utils import TestServer
        return TestServer(self.fake_atv)

    def get_connected_device(self):
        details = AppleTVDevice('Apple TV', '127.0.0.1', HSGID, self.app.port)
        return connect_to_apple_tv(details, self.loop)

    @unittest_run_loop
    def test_login_failed(self):
        self.usecase.make_login_fail()

        with self.assertRaises(exceptions.AuthenticationError):
            yield from self.atv.login()

        yield from self.atv.logout()

    @unittest_run_loop
    def test_login_succeed(self):
        session_id = yield from self.atv.login()
        self.assertEqual(SESSION_ID, session_id)
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_play(self):
        yield from self.atv.remote_control.play()
        self.assertEqual(self.fake_atv.last_button_pressed, 'play')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_pause(self):
        yield from self.atv.remote_control.pause()
        self.assertEqual(self.fake_atv.last_button_pressed, 'pause')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_next(self):
        yield from self.atv.remote_control.next()
        self.assertEqual(self.fake_atv.last_button_pressed, 'nextitem')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_previous(self):
        yield from self.atv.remote_control.previous()
        self.assertEqual(self.fake_atv.last_button_pressed, 'previtem')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_select(self):
        yield from self.atv.remote_control.select()
        self.assertEqual(self.fake_atv.last_button_pressed, 'select')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_menu(self):
        yield from self.atv.remote_control.menu()
        self.assertEqual(self.fake_atv.last_button_pressed, 'menu')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_button_topmenu(self):
        yield from self.atv.remote_control.topmenu()
        self.assertEqual(self.fake_atv.last_button_pressed, 'topmenu')
        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_artwork(self):
        expected_artwork = b'12345'
        self.usecase.change_artwork(expected_artwork)

        artwork = yield from self.atv.metadata.artwork()
        self.assertEqual(artwork, expected_artwork)
        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_artwork_none_if_not_available(self):
        self.usecase.change_artwork(b'')

        artwork = yield from self.atv.metadata.artwork()
        self.assertIsNone(artwork)
        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_none_type_when_not_playing(self):
        self.usecase.nothing_playing()

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_UNKNOWN)
        self.assertEqual(playing.play_state, const.PLAY_STATE_NO_MEDIA)

        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_video_paused(self):
        self.usecase.video_playing(paused=True, title='dummy',
                                   total_time=123, position=3)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_VIDEO)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PAUSED)
        self.assertEqual(playing.title, 'dummy')
        self.assertEqual(playing.total_time, 123)
        self.assertEqual(playing.position, 3)

        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_video_playing(self):
        self.usecase.video_playing(paused=False, title='video',
                                   total_time=40, position=10)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_VIDEO)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PLAYING)
        self.assertEqual(playing.title, 'video')
        self.assertEqual(playing.total_time, 40)
        self.assertEqual(playing.position, 10)

        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_music_paused(self):
        self.usecase.music_playing(paused=True, title='music',
                                   artist='artist', album='album',
                                   total_time=222, position=49)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_MUSIC)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PAUSED)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'artist')
        self.assertEqual(playing.album, 'album')
        self.assertEqual(playing.total_time, 222)
        self.assertEqual(playing.position, 49)

        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_music_playing(self):
        self.usecase.music_playing(paused=False, title='music',
                                   artist='test1', album='test2',
                                   total_time=2, position=1)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_MUSIC)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PLAYING)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'test1')
        self.assertEqual(playing.album, 'test2')
        self.assertEqual(playing.total_time, 2)
        self.assertEqual(playing.position, 1)

        yield from self.atv.logout()

    @unittest_run_loop
    def test_seek_in_playing_media(self):
        yield from self.atv.remote_control.set_position(60)
        self.assertEqual(self.fake_atv.responses['playing'].position, 60000)
        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_loading(self):
        self.usecase.media_is_loading()

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.play_state, const.PLAY_STATE_LOADING)
        yield from self.atv.logout()
