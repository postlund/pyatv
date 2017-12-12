"""Functional tests using the API with a fake Apple TV."""

import pyatv
import asyncio
import ipaddress

from tests.log_output_handler import LogOutputHandler
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import (AppleTVDevice, connect_to_apple_tv, const,
                   exceptions, pairing)
from tests.fake_apple_tv import (
    FakeAppleTV, AppleTVUseCases, DEVICE_PIN, DEVICE_CREDENTIALS)
from tests import (utils, zeroconf_stub)

HSGID = '12345-6789-0'
PAIRING_GUID = '0x0000000000000001'
SESSION_ID = 55555
REMOTE_NAME = 'pyatv remote'
PIN_CODE = 1234

EXPECTED_ARTWORK = b'1234'
AIRPLAY_STREAM = 'http://stream'

# This is valid for the PAIR in the pairing module and pin 1234
# (extracted form a real device)
PAIRINGCODE = '690E6FF61E0D7C747654A42AED17047D'

HOMESHARING_SERVICE_1 = zeroconf_stub.homesharing_service(
    'AAAA', b'Apple TV 1', '10.0.0.1', b'aaaa')
HOMESHARING_SERVICE_2 = zeroconf_stub.homesharing_service(
    'BBBB', b'Apple TV 2', '10.0.0.2', b'bbbb')


class FunctionalTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.atv = self.get_connected_device(HSGID)
        self.log_handler = LogOutputHandler(self)

        # Make sleep calls do nothing to not slow down tests
        @asyncio.coroutine
        def fake_sleep(self, time=None, loop=None):
            pass
        asyncio.sleep = fake_sleep

        # TODO: currently stubs internal method, should provide stub
        # for netifaces later
        pairing._get_private_ip_addresses = \
            lambda: [ipaddress.ip_address('10.0.0.1')]

    def tearDown(self):
        self.loop.run_until_complete(self.atv.logout())
        AioHTTPTestCase.tearDown(self)
        self.log_handler.tearDown()

    @asyncio.coroutine
    def get_application(self, loop=None):
        self.fake_atv = FakeAppleTV(
            self.loop, HSGID, PAIRING_GUID, SESSION_ID, self)
        self.usecase = AppleTVUseCases(self.fake_atv)
        return self.fake_atv

    def get_connected_device(self, identifier):
        details = AppleTVDevice(
            'Apple TV', '127.0.0.1', identifier,
            self.server.port, self.server.port)
        return connect_to_apple_tv(details, self.loop)

    # This is not a pretty test and it does crazy things. Should probably be
    # re-written later but will do for now.
    @unittest_run_loop
    def test_pairing_with_device(self):
        zeroconf = zeroconf_stub.stub(pairing)
        self.usecase.pairing_response(REMOTE_NAME, PAIRINGCODE)

        handler = pyatv.pair_with_apple_tv(
            self.loop, PIN_CODE, REMOTE_NAME,
            pairing_guid=pairing.DEFAULT_PAIRING_GUID)
        yield from handler.start(zeroconf)
        yield from self.usecase.act_on_bonjour_services(zeroconf)
        yield from handler.stop()

        self.assertTrue(handler.has_paired, msg='did not pair with device')

    @unittest_run_loop
    def test_device_authentication(self):
        # Credentials used for device authentication
        yield from self.atv.airplay.load_credentials(DEVICE_CREDENTIALS)

        # Perform authentication
        yield from self.atv.airplay.start_authentication()
        yield from self.atv.airplay.finish_authentication(DEVICE_PIN)

        # Verify credentials are authenticated
        self.assertTrue((yield from self.atv.airplay.verify_authenticated()))

    @unittest_run_loop
    def test_play_url(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        yield from self.atv.airplay.play_url(
            AIRPLAY_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AIRPLAY_STREAM)

    @unittest_run_loop
    def test_play_url_authenticated(self):
        self.usecase.airplay_require_authentication()
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        yield from self.atv.airplay.load_credentials(DEVICE_CREDENTIALS)

        yield from self.atv.airplay.play_url(
            AIRPLAY_STREAM, port=self.server.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AIRPLAY_STREAM)

    @unittest_run_loop
    def test_login_failed(self):
        # Twice since the client will retry one time
        self.usecase.make_login_fail()
        self.usecase.make_login_fail()

        with self.assertRaises(exceptions.AuthenticationError):
            yield from self.atv.login()

    # This test verifies issue #2 (automatic re-login). It uses the artwork
    # API, but it could have been any API since the login code is the same.
    @unittest_run_loop
    def test_relogin_if_session_expired(self):
        yield from self.atv.login()

        # Here, we are logged in and currently have a asession id. These
        # usescases will result in being logged out (HTTP 403) and forcing a
        # re-login with a new session id (1234)
        self.usecase.force_relogin(1234)
        self.usecase.artwork_no_permission()
        self.usecase.change_artwork(EXPECTED_ARTWORK)

        artwork = yield from self.atv.metadata.artwork()
        self.assertEqual(artwork, EXPECTED_ARTWORK)

    @unittest_run_loop
    def test_login_with_hsgid_succeed(self):
        session_id = yield from self.atv.login()
        self.assertEqual(SESSION_ID, session_id)

    @unittest_run_loop
    def test_login_with_pairing_guid_succeed(self):
        yield from self.atv.logout()
        self.atv = self.get_connected_device(PAIRING_GUID)
        session_id = yield from self.atv.login()
        self.assertEqual(SESSION_ID, session_id)

    # When moving around using the arrow keys, a sequence of seven
    # different requests are sent to the device. To simplify the
    # test, verify that seven commands were sent and that the last
    # command matches the expected arrow key. This does not guarantee
    # that the earlier six commands were correct, but it's good
    # enough to keep the tests clean.

    @unittest_run_loop
    def test_button_up(self):
        yield from self.atv.remote_control.up()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'up')

    @unittest_run_loop
    def test_button_down(self):
        yield from self.atv.remote_control.down()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'down')

    @unittest_run_loop
    def test_button_left(self):
        yield from self.atv.remote_control.left()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'left')

    @unittest_run_loop
    def test_button_right(self):
        yield from self.atv.remote_control.right()
        self.assertEqual(self.fake_atv.buttons_press_count, 7)
        self.assertEqual(self.fake_atv.last_button_pressed, 'right')

    @unittest_run_loop
    def test_button_play(self):
        yield from self.atv.remote_control.play()
        self.assertEqual(self.fake_atv.last_button_pressed, 'play')

    @unittest_run_loop
    def test_button_pause(self):
        yield from self.atv.remote_control.pause()
        self.assertEqual(self.fake_atv.last_button_pressed, 'pause')

    @unittest_run_loop
    def test_button_stop(self):
        yield from self.atv.remote_control.stop()
        self.assertEqual(self.fake_atv.last_button_pressed, 'stop')

    @unittest_run_loop
    def test_button_next(self):
        yield from self.atv.remote_control.next()
        self.assertEqual(self.fake_atv.last_button_pressed, 'nextitem')

    @unittest_run_loop
    def test_button_previous(self):
        yield from self.atv.remote_control.previous()
        self.assertEqual(self.fake_atv.last_button_pressed, 'previtem')

    @unittest_run_loop
    def test_button_select(self):
        yield from self.atv.remote_control.select()
        self.assertEqual(self.fake_atv.last_button_pressed, 'select')

    @unittest_run_loop
    def test_button_menu(self):
        yield from self.atv.remote_control.menu()
        self.assertEqual(self.fake_atv.last_button_pressed, 'menu')

    @unittest_run_loop
    def test_button_top_menu(self):
        yield from self.atv.remote_control.top_menu()
        self.assertEqual(self.fake_atv.last_button_pressed, 'topmenu')

    def test_metadata_device_id(self):
        # This is a reference case for a server running at 127.0.0.1:3689
        self.assertEqual(
            self.atv.metadata.device_id,
            '12ca17b49af2289436f303e0166030a21e525d266e209267433801a8fd4071a0')

    @unittest_run_loop
    def test_metadata_artwork(self):
        self.usecase.change_artwork(EXPECTED_ARTWORK)

        artwork = yield from self.atv.metadata.artwork()
        self.assertEqual(artwork, EXPECTED_ARTWORK)

    @unittest_run_loop
    def test_metadata_artwork_url(self):
        self.usecase.change_artwork(EXPECTED_ARTWORK)

        # Must be logged in to have valid session id
        yield from self.atv.login()

        # URL to artwork
        artwork_url = yield from self.atv.metadata.artwork_url()

        # Fetch artwork with a GET request to ensure it works
        artwork, _ = yield from utils.simple_get(artwork_url, self.loop)
        self.assertEqual(artwork, EXPECTED_ARTWORK)

    @unittest_run_loop
    def test_metadata_artwork_none_if_not_available(self):
        self.usecase.change_artwork(b'')

        artwork = yield from self.atv.metadata.artwork()
        self.assertIsNone(artwork)

    @unittest_run_loop
    def test_metadata_none_type_when_not_playing(self):
        self.usecase.nothing_playing()

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_UNKNOWN)
        self.assertEqual(playing.play_state, const.PLAY_STATE_NO_MEDIA)

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

    @unittest_run_loop
    def test_metadata_music_paused(self):
        self.usecase.music_playing(paused=True, title='music',
                                   artist='artist', album='album',
                                   total_time=222, position=49,
                                   genre='genre')

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_MUSIC)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PAUSED)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'artist')
        self.assertEqual(playing.album, 'album')
        self.assertEqual(playing.genre, 'genre')
        self.assertEqual(playing.total_time, 222)
        self.assertEqual(playing.position, 49)

    @unittest_run_loop
    def test_metadata_music_playing(self):
        self.usecase.music_playing(paused=False, title='music',
                                   artist='test1', album='test2',
                                   total_time=2, position=1,
                                   genre='genre')

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.media_type, const.MEDIA_TYPE_MUSIC)
        self.assertEqual(playing.play_state, const.PLAY_STATE_PLAYING)
        self.assertEqual(playing.title, 'music')
        self.assertEqual(playing.artist, 'test1')
        self.assertEqual(playing.album, 'test2')
        self.assertEqual(playing.genre, 'genre')
        self.assertEqual(playing.total_time, 2)
        self.assertEqual(playing.position, 1)

    @unittest_run_loop
    def test_push_updates(self):

        class PushListener:
            def __init__(self):
                self.playing = None

            def playstatus_update(self, updater, playstatus):
                self.playing = playstatus
                updater.stop()

            @staticmethod
            def playstatus_error(updater, exception):
                pass

        # Prepare two playstatus updates in the fake device. Take note: every
        # time start() is called, revision 0 should be used first. This will
        # make sure that we always get a push update instantly. Otherwise we
        # might hang and wait for an update.
        self.usecase.video_playing(paused=False, title='video1',
                                   total_time=40, position=10,
                                   revision=0)
        self.usecase.video_playing(paused=True, title='video2',
                                   total_time=30, position=20,
                                   revision=0)

        # Poll the first one ("video1")
        yield from self.atv.metadata.playing()

        # Setup push updates which will instantly get the next one ("video2")
        listener = PushListener()
        self.atv.push_updater.listener = listener
        yield from self.atv.push_updater.start()

        # Check that we got the right one
        self.assertIsNotNone(listener.playing)
        self.assertEqual(listener.playing.title, 'video2')

    @unittest_run_loop
    def test_shuffle_state(self):
        self.usecase.example_video(shuffle=False)
        self.usecase.example_video(shuffle=True)

        playing = yield from self.atv.metadata.playing()
        self.assertFalse(playing.shuffle)

        playing = yield from self.atv.metadata.playing()
        self.assertTrue(playing.shuffle)

    @unittest_run_loop
    def test_repeat_state(self):
        self.usecase.example_video(repeat=const.REPEAT_STATE_OFF)
        self.usecase.example_video(repeat=const.REPEAT_STATE_TRACK)
        self.usecase.example_video(repeat=const.REPEAT_STATE_ALL)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.repeat, const.REPEAT_STATE_OFF)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.repeat, const.REPEAT_STATE_TRACK)

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.repeat, const.REPEAT_STATE_ALL)

    @unittest_run_loop
    def test_set_shuffle(self):
        yield from self.atv.remote_control.set_shuffle(1)
        self.assertEqual(self.fake_atv.properties['dacp.shufflestate'], 1)

        yield from self.atv.remote_control.set_shuffle(0)
        self.assertEqual(self.fake_atv.properties['dacp.shufflestate'], 0)

    @unittest_run_loop
    def test_set_repeat(self):
        yield from self.atv.remote_control.set_repeat(1)
        self.assertEqual(self.fake_atv.properties['dacp.repeatstate'], 1)

        yield from self.atv.remote_control.set_repeat(2)
        self.assertEqual(self.fake_atv.properties['dacp.repeatstate'], 2)

    @unittest_run_loop
    def test_seek_in_playing_media(self):
        yield from self.atv.remote_control.set_position(60)
        self.assertEqual(self.fake_atv.properties['dacp.playingtime'], 60000)

    @unittest_run_loop
    def test_metadata_loading(self):
        self.usecase.media_is_loading()

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.play_state, const.PLAY_STATE_LOADING)
