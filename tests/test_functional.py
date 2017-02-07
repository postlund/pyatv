"""Functional tests using the API with a fake Apple TV."""

import pyatv
import aiohttp
import ipaddress

from tests.log_output_handler import LogOutputHandler
from aiohttp.test_utils import (AioHTTPTestCase, unittest_run_loop)

from pyatv import (AppleTVDevice, connect_to_apple_tv, const,
                   exceptions, dmap, tag_definitions, pairing)
from tests.fake_apple_tv import (FakeAppleTV, AppleTVUseCases)
from tests import zeroconf_stub

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


class FunctionalTest(AioHTTPTestCase):

    def setUp(self):
        AioHTTPTestCase.setUp(self)
        self.atv = self.get_connected_device(HSGID)
        self.log_handler = LogOutputHandler(self)

    def tearDown(self):
        AioHTTPTestCase.tearDown(self)
        self.log_handler.tearDown()

    def get_app(self, loop):
        self.fake_atv = FakeAppleTV(
            loop, HSGID, PAIRING_GUID, SESSION_ID, self)
        self.usecase = AppleTVUseCases(self.fake_atv)

        # Import TestServer here and not globally, otherwise py.test will
        # complain when running:
        #
        #   test_functional.py cannot collect test class 'TestServer'
        #   because it has a __init__ constructor
        from aiohttp.test_utils import TestServer
        return TestServer(self.fake_atv)

    def get_connected_device(self, identifier):
        details = AppleTVDevice(
            'Apple TV', '127.0.0.1', identifier, self.app.port)
        return connect_to_apple_tv(details, self.loop)

    @unittest_run_loop
    def test_scan_for_apple_tvs(self):
        zeroconf_stub.stub(pyatv, zeroconf_stub.homesharing_service(
            'AAAA', b'Apple TV', '10.0.0.1', b'aaaa'))

        atvs = yield from pyatv.scan_for_apple_tvs(self.loop, timeout=0)
        self.assertEqual(len(atvs), 1)
        self.assertEqual(atvs[0].name, 'Apple TV')
        self.assertEqual(atvs[0].address, ipaddress.ip_address('10.0.0.1'))
        self.assertEqual(atvs[0].login_id, 'aaaa')
        self.assertEqual(atvs[0].port, 3689)

    # This is not a pretty test and it does crazy things. Should probably be
    # re-written later but will do for now.
    @unittest_run_loop
    def test_pairing_with_device(self):
        zeroconf_stub.stub(pairing)

        # Start pairing process
        handler = pyatv.pair_with_apple_tv(self.loop, PIN_CODE, REMOTE_NAME)
        yield from handler.start()

        # Verify that bonjour service was published
        zeroconf = zeroconf_stub.instance
        self.assertEqual(len(zeroconf.registered_services), 1,
                         msg='no zeroconf service registered')

        service = zeroconf.registered_services[0]
        self.assertEqual(service.properties['DvNm'], 'pyatv remote',
                         msg='remote name does not match')

        # Extract port from service (as it is randomized) and request pairing
        # with the web server.
        server = 'http://127.0.0.1:{}'.format(service.port)
        url = '{}/pairing?pairingcode={}&servicename=test'.format(
            server, PAIRINGCODE)
        session = aiohttp.ClientSession(loop=self.loop)
        response = yield from session.request('GET', url)
        self.assertEqual(response.status, 200,
                         msg='pairing failed')

        # Verify content returned in pairingresponse
        data = yield from response.content.read()
        parsed = dmap.parse(data, tag_definitions.lookup_tag)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmpg'), 1)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmnm'), REMOTE_NAME)
        self.assertEqual(dmap.first(parsed, 'cmpa', 'cmty'), 'ipod')

        response.close()
        yield from session.close()
        yield from handler.stop()
        yield from self.atv.logout()

    @unittest_run_loop
    def test_play_url(self):
        self.usecase.airplay_playback_idle()
        self.usecase.airplay_playback_playing()
        self.usecase.airplay_playback_idle()

        yield from self.atv.remote_control.play_url(
            AIRPLAY_STREAM, 0, port=self.app.port)

        self.assertEqual(self.fake_atv.last_airplay_url, AIRPLAY_STREAM)

    @unittest_run_loop
    def test_login_failed(self):
        # Twice since the client will retry one time
        self.usecase.make_login_fail()
        self.usecase.make_login_fail()

        with self.assertRaises(exceptions.AuthenticationError):
            yield from self.atv.login()

        yield from self.atv.logout()

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

        yield from self.atv.logout()

    @unittest_run_loop
    def test_login_with_hsgid_succeed(self):
        session_id = yield from self.atv.login()
        self.assertEqual(SESSION_ID, session_id)
        yield from self.atv.logout()

    @unittest_run_loop
    def test_login_with_pairing_guid_succeed(self):
        self.atv = self.get_connected_device(PAIRING_GUID)
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
        self.usecase.change_artwork(EXPECTED_ARTWORK)

        artwork = yield from self.atv.metadata.artwork()
        self.assertEqual(artwork, EXPECTED_ARTWORK)
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
        self.assertEqual(self.fake_atv.properties['dacp.playingtime'], 60000)
        yield from self.atv.logout()

    @unittest_run_loop
    def test_metadata_loading(self):
        self.usecase.media_is_loading()

        playing = yield from self.atv.metadata.playing()
        self.assertEqual(playing.play_state, const.PLAY_STATE_LOADING)
        yield from self.atv.logout()
