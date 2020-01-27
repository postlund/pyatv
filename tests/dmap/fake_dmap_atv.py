"""Fake DMAP Apple TV device for tests."""

import logging

from collections import namedtuple

from aiohttp import web

from pyatv.dmap import (parser, tags, tag_definitions)
from tests.airplay.fake_airplay_device import (
    FakeAirPlayDevice, AirPlayUseCases)
from tests import utils

_LOGGER = logging.getLogger(__name__)

EXPECTED_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip',
    'Client-DAAP-Version': '3.13',
    'Client-ATV-Sharing-Version': '1.2',
    'Client-iTunes-Sharing-Version': '3.15',
    'User-Agent': 'Remote/1021',
    'Viewer-Only-Client': '1',
}

LoginResponse = namedtuple('LoginResponse', 'session, status')
ArtworkResponse = namedtuple('ArtworkResponse', 'content, status')
AirPlayPlaybackResponse = namedtuple('AirPlayPlaybackResponse', 'content')
PairingResponse = namedtuple('PairingResponse', 'remote_name, pairing_code')


DEVICE_IDENTIFIER = '75FBEEC773CFC563'
DEVICE_AUTH_KEY = \
    '8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493'
DEVICE_PIN = 2271
DEVICE_CREDENTIALS = DEVICE_IDENTIFIER + ':' + DEVICE_AUTH_KEY


class PlayingResponse:
    """Response returned by command playstatusupdate."""

    def __init__(self, revision=0, shuffle=False, **kwargs):
        """Initialize a new PlayingResponse."""
        self.paused = kwargs.get('paused', None)
        self.title = kwargs.get('title', None)
        self.artist = kwargs.get('artist', None)
        self.album = kwargs.get('album', None)
        self.genre = kwargs.get('genre', None)
        self.total_time = kwargs.get('total_time', None)
        self.position = kwargs.get('position', None)
        self.mediakind = kwargs.get('mediakind', None)
        self.playstatus = kwargs.get('playstatus', None)
        self.repeat = kwargs.get('repeat', None)
        self.revision = revision
        self.shuffle = shuffle
        self.force_close = kwargs.get('force_close', False)


class FakeAppleTV(FakeAirPlayDevice):
    """Implementation of a fake DMAP Apple TV."""

    def __init__(self, hsgid, pairing_guid, session_id, testcase):
        """Initialize a new FakeAppleTV."""
        super().__init__(testcase)

        self.responses['login'] = [LoginResponse(session_id, 200)]
        self.responses['artwork'] = []
        self.responses['playing'] = []
        self.responses['pairing'] = []
        self.hsgid = hsgid
        self.pairing_guid = pairing_guid
        self.session = None
        self.last_button_pressed = None
        self.buttons_press_count = 0

        self.app.router.add_get('/login', self.handle_login)
        self.app.router.add_get(
            '/ctrl-int/1/playstatusupdate', self.handle_playstatus)
        self.app.router.add_post(
            '/ctrl-int/1/controlpromptentry', self.handle_remote_button)
        self.app.router.add_get(
            '/ctrl-int/1/nowplayingartwork', self.handle_artwork)
        self.app.router.add_post(
            '/ctrl-int/1/setproperty', self.handle_set_property)
        for button in ['play', 'pause', 'stop', 'nextitem', 'previtem']:
            self.app.router.add_post('/ctrl-int/1/' + button,
                                     self.handle_playback_button)

    async def handle_login(self, request):
        """Handle login requests."""
        self._verify_headers(request)
        self._verify_auth_parameters(
            request, check_login_id=True, check_session=False)

        data = self._get_response('login')
        mlid = tags.uint32_tag('mlid', data.session)
        mlog = tags.container_tag('mlog', mlid)
        self.session = data.session
        return web.Response(body=mlog, status=data.status)

    async def handle_playback_button(self, request):
        """Handle playback buttons."""
        self._verify_auth_parameters(request)
        self.last_button_pressed = request.rel_url.path.split('/')[-1]
        self.buttons_press_count += 1
        return web.Response(status=200)

    async def handle_remote_button(self, request):
        """Handle remote control buttons."""
        self._verify_auth_parameters(request)
        content = await request.content.read()
        parsed = parser.parse(content, tag_definitions.lookup_tag)
        self.last_button_pressed = self._convert_button(parsed)
        self.buttons_press_count += 1
        return web.Response(status=200)

    def _convert_button(self, data):
        value = parser.first(data, 'cmbe')

        # Consider navigation buttons if six commands have been received
        if self.buttons_press_count == 6:
            if value == 'touchUp&time=6&point=20,250':
                return 'up'
            elif value == 'touchUp&time=6&point=20,275':
                return 'down'
            elif value == 'touchUp&time=7&point=50,100':
                return 'left'
            elif value == 'touchUp&time=7&point=75,100':
                return 'right'

        return value

    async def handle_artwork(self, request):
        """Handle artwork requests."""
        self._verify_auth_parameters(request)
        artwork = self._get_response('artwork')
        return web.Response(body=artwork.content, status=artwork.status)

    async def handle_playstatus(self, request):
        """Handle  playstatus (currently playing) requests."""
        self._verify_auth_parameters(request)

        body = b''
        playing = self._get_response('playing')

        # Check if connection should be closed to trigger error on client side
        if playing.force_close:
            await request.transport.close()

        # Make sure revision matches
        revision = int(request.rel_url.query['revision-number'])
        if playing.revision != revision:
            # Not a valid response as a real device, just to make tests fail
            return web.Response(status=500)

        if playing.paused is not None:
            body += tags.uint32_tag('caps', 3 if playing.paused else 4)

        if playing.title is not None:
            body += tags.string_tag('cann', playing.title)

        if playing.artist is not None:
            body += tags.string_tag('cana', playing.artist)

        if playing.album is not None:
            body += tags.string_tag('canl', playing.album)

        if playing.genre is not None:
            body += tags.string_tag('cang', playing.genre)

        if playing.total_time is not None:
            total_time = playing.total_time * 1000  # sec -> ms
            body += tags.uint32_tag('cast', total_time)

            if playing.position is not None:
                pos = (playing.total_time - playing.position)
                print(playing.total_time, playing.position)
                body += tags.uint32_tag('cant', pos * 1000)  # sec -> ms

        if playing.mediakind is not None:
            body += tags.uint32_tag('cmmk', playing.mediakind)

        if playing.playstatus is not None:
            body += tags.uint32_tag('caps', playing.playstatus)

        if playing.repeat is not None:
            body += tags.uint8_tag('carp', playing.repeat)

        body += tags.uint8_tag('cash', playing.shuffle)
        body += tags.uint32_tag('cmsr', playing.revision + 1)

        return web.Response(
            body=tags.container_tag('cmst', body), status=200)

    async def handle_set_property(self, request):
        """Handle property changes."""
        self._verify_auth_parameters(request)
        if 'dacp.playingtime' in request.rel_url.query:
            playtime = int(request.rel_url.query['dacp.playingtime'])
            self._get_response('playing').position = int(playtime / 1000)
        elif 'dacp.shufflestate' in request.rel_url.query:
            shuffle = int(request.rel_url.query['dacp.shufflestate'])
            self._get_response('playing').shuffle = (shuffle == 1)
        elif 'dacp.repeatstate' in request.rel_url.query:
            repeat = int(request.rel_url.query['dacp.repeatstate'])
            self._get_response('playing').repeat = repeat
        else:
            web.Response(body=b'', status=500)

        return web.Response(body=b'', status=200)

    async def trigger_bonjour(self, stubbed_zeroconf):
        """Act upon available Bonjour services."""
        # Add more services here when needed
        for service in stubbed_zeroconf.registered_services:
            if service.type != '_touch-remote._tcp.local.':
                continue

            # Look for the response matching this remote
            remote_name = service.properties[b'DvNm']
            for response in self.responses['pairing']:
                if response.remote_name == remote_name:
                    return await self.perform_pairing(response, service.port)

    async def perform_pairing(self, pairing_response, port):
        """Pair with a remote client.

        This will perform a GET-request to the specified port and hand over
        information to the client (pyatv) so that the pairing process can be
        completed.
        """
        server = 'http://127.0.0.1:{}'.format(port)
        url = '{}/pairing?pairingcode={}&servicename=test'.format(
            server, pairing_response.pairing_code)
        data, _ = await utils.simple_get(url)

        # Verify content returned in pairingresponse
        parsed = parser.parse(data, tag_definitions.lookup_tag)
        self.tc.assertEqual(parser.first(parsed, 'cmpa', 'cmpg'), 1)
        self.tc.assertEqual(parser.first(parsed, 'cmpa', 'cmnm'),
                            pairing_response.remote_name)
        self.tc.assertEqual(parser.first(parsed, 'cmpa', 'cmty'), 'iPhone')

    # Verifies that all needed headers are included in the request. Should be
    # checked in all requests, but that seems a bit too much and not that
    # necessary.
    def _verify_headers(self, request):
        for header in EXPECTED_HEADERS:
            self.tc.assertIn(header, request.headers)
            self.tc.assertEqual(request.headers[header],
                                EXPECTED_HEADERS[header])

    # This method makes sure that the correct login id and/or session id is
    # included in the GET-parameters. As this is extremely important for
    # anything to work, this should be verified in all requests.
    def _verify_auth_parameters(self,
                                request,
                                check_login_id=False,
                                check_session=True):
        params = request.rel_url.query

        # Either hsgid or pairing-guid should be present
        if check_login_id:
            if 'hsgid' in params:
                self.tc.assertEqual(params['hsgid'], self.hsgid,
                                    msg='hsgid does not match')
            elif 'pairing-guid' in params:
                self.tc.assertEqual(params['pairing-guid'], self.pairing_guid,
                                    msg='pairing-guid does not match')
            else:
                self.tc.assertTrue(False, 'hsgid or pairing-guid not found')

        if check_session:
            self.tc.assertEqual(int(params['session-id']), self.session,
                                msg='session id does not match')


class AppleTVUseCases(AirPlayUseCases):
    """Wrapper for altering behavior of a FakeAppleTV instance.

    Extend and use this class to alter behavior of a fake Apple TV device.
    """

    def __init__(self, fake_apple_tv):
        """Initialize a new AppleTVUseCases."""
        self.device = fake_apple_tv

    def force_relogin(self, session):
        """Call this method to change current session id."""
        self.device.responses['login'].append(LoginResponse(session, 200))

    def make_login_fail(self, immediately=True):
        """Call this method to make login fail with response 503."""
        response = LoginResponse(0, 503)
        if immediately:
            self.device.responses['login'].append(response)
        else:
            self.device.responses['login'].insert(0, response)

    def change_artwork(self, artwork, mimetype, identifier=None):
        """Call this method to change artwork response."""
        self.device.responses['artwork'].append(
            ArtworkResponse(artwork, 200))

    def artwork_no_permission(self):
        """Make artwork fail with no permission.

        This corresponds to have been logged out for some reason.
        """
        self.device.responses['artwork'].insert(
            0, ArtworkResponse(None, 403))

    def nothing_playing(self):
        """Call this method to put device in idle state."""
        self.device.responses['playing'].insert(0, PlayingResponse())

    def server_closes_connection(self):
        """Call this method to force server to close connection on request."""
        self.device.responses['playing'].insert(
            0, PlayingResponse(force_close=True))

    def example_video(self, **kwargs):
        """Play some example video."""
        self.video_playing(paused=True, title='dummy',
                           total_time=123, position=3, **kwargs)

    def video_playing(self, paused, title, total_time, position, **kwargs):
        """Call this method to change what is currently plaing to video."""
        revision = 0
        shuffle = False
        repeat = None
        if 'revision' in kwargs:
            revision = kwargs['revision']
        if 'shuffle' in kwargs:
            shuffle = kwargs['shuffle'].value
        if 'repeat' in kwargs:
            repeat = kwargs['repeat'].value
        self.device.responses['playing'].insert(0, PlayingResponse(
            revision=revision,
            paused=paused, title=title,
            total_time=total_time, position=position,
            mediakind=3, shuffle=shuffle, repeat=repeat))

    def music_playing(self, paused, artist, album, title, genre,
                      total_time, position):
        """Call this method to change what is currently plaing to music."""
        self.device.responses['playing'].insert(0, PlayingResponse(
            paused=paused, title=title,
            artist=artist, album=album,
            total_time=total_time,
            position=position, genre=genre,
            mediakind=2))

    def media_is_loading(self):
        """Call this method to put device in a loading state."""
        self.device.responses['playing'].insert(0, PlayingResponse(
            playstatus=1))

    def pairing_response(self, remote_name, expected_pairing_code):
        """Reponse when a pairing request is made."""
        self.device.responses['pairing'].insert(0, PairingResponse(
            remote_name, expected_pairing_code))

    async def act_on_bonjour_services(self, stubbed_zeroconf):
        """Act on available Bonjour services.

        This will make the device look at published services and perform
        actions base on these. Most imporant for the pairing process.
        """
        await self.device.trigger_bonjour(stubbed_zeroconf)
