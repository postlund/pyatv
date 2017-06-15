"""Fake Apple TV device for tests.

This is an implementation of an Apple TV device that can be used to verify
functionality in tests. It is possible to specify return values for different
kinds of responses. Also, it performs various sanity checks, like that auth
information is correct and headers are present.
"""

import re
import asyncio
import plistlib
import binascii
from collections import namedtuple

from aiohttp import web

from pyatv import (tags, dmap, tag_definitions)
from tests import utils


EXPECTED_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip',
    'Client-DAAP-Version': '3.12',
    'Client-ATV-Sharing-Version': '1.2',
    'Client-iTunes-Sharing-Version': '3.10',
    'User-Agent': 'TVRemote/186 CFNetwork/808.1.4 Darwin/16.1.0',
    'Viewer-Only-Client': '1',
}

# --- START AUTHENTICATION DATA VALID SESSION (FROM DEVICE) ---

DEVICE_IDENTIFIER = '75FBEEC773CFC563'
DEVICE_AUTH_KEY = \
    '8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493'
DEVICE_PIN = 2271
DEVICE_CREDENTIALS = DEVICE_IDENTIFIER + ':' + DEVICE_AUTH_KEY

# pylint: disable=E501
# For authentication
_DEVICE_AUTH_STEP1 = b'62706c6973743030d201020304566d6574686f6454757365725370696e5f101037354642454543373733434643353633080d14191d0000000000000101000000000000000500000000000000000000000000000030'  # noqa
_DEVICE_AUTH_STEP1_RESP = b'62706c6973743030d20102030452706b5473616c744f1101008817e16146c7d12b45e810b0bf190a4ccb25d9a20a8d0504d874daa8db5574c51c8b33703a95c00bdbe99c8c3745d1ef1b38e538edfd98e09ec029effe6f28b3b54a1bd41c28d8f33da6f5ac9327bfce9a66869dae645b5cbd2c6b8fbe14a30ad4f8598154f2ef7f4f52cee3e3042a69780463c26bbb764870eb1995b26a2a4ade05564836d788baf07469a143c410ea9d07a068eb790b2b0aa5b86c990636814e3fa1a899ceba1af45b211ca4bd3b5b66ffaf16051a4f851e120476054258f257b8521a068907ad5e9c7220d5cef9aa072dec9edb7ebf633cad4d52d105cf58440f17e236332b0b26539851a879e9ac8d3c2da4c590785468e590296d39d7374f1010fca6dcb6b83a7c716a692f806e9159540008000d001000150119000000000000020100000000000000050000000000000000000000000000012c'  # noqa
_DEVICE_AUTH_STEP2 = b'62706c6973743030d20102030452706b5570726f6f664f1101000819b6ba7feead4753809314e2b4c5db9109f737a0fc70b758342b6bbf536fae4e40cf94607588abb17c2076030cc00c2c1fa5fc3b3dfe8aa1ec2f23f74d917c0792fbf02f131377dfb8ae2a1656ceaa0a36bb3ab752586e1af17e1d5ef24ce083f3f9298d0be761f26c0d48af86510bf9aac7940cf90bff6bd214cf34b5536856c80f076cfbe06fd69af9d6a07a6d3ac580dfffc8a40b9730575a16c5046cd73321a944880dcf9fac952afc7ffd2d135e57ec208b11cef22b734f331ad4d8c9a737b588f7b30bd5210c65cae2ba0226f69ce7b505771faa63af89ed2f9e8325d7d5f3a2da7412f9d837860632d7f81b7fa5e09dd85e1539184070c0fa8433c24f1014fc6286910833d3e7ae0631d47ddbb0f492ef85b80008000d00100016011a0000000000000201000000000000000500000000000000000000000000000131'  # noqa
_DEVICE_AUTH_STEP2_RESP = b'62706c6973743030d101025570726f6f664f101484a88548b12bce122ad1cea6caff312630edcf27080b110000000000000101000000000000000300000000000000000000000000000028'  # noqa
_DEVICE_AUTH_STEP3 = b'62706c6973743030d20102030457617574685461675365706b4f101052a92f8712c6ea417f3adb3d03d8e5634f1020ff07fc8520d10728e6f2ab0a0245dfa20709b5d1ae5f9a19328b0663ba9414f2080d15192c000000000000010100000000000000050000000000000000000000000000004f'  # noqa
_DEVICE_AUTH_STEP3_RESP = b'62706c6973743030d2010203045365706b57617574685461674f10206285b20afad4cefe1fce40cee685ab072c75240cb47fb71bc3b3d03dca52dc5d4f1010893eb8e5ae418b245e9b1bf7cba9116b080d11193c000000000000010100000000000000050000000000000000000000000000004f'  # noqa

# For verification
_DEVICE_VERIFY_STEP1 = b'01000000891bae9f581f68f9c9933c4f713fbb5b9de639ec7df5d0a4fd4f342f1c21aa6a5e9d1e843302d6265b8c48dd169e273460e567916b0b36280ac071001118f6b2'  # noqa
_DEVICE_VERIFY_STEP1_RESP = b'3221371da9f00d035955caa912455fd2acee68117b557f25e39168746af4b631cfab7b2c6d0b58e96cc10af884f5a4cdef8063858a9d9c04e866743cf4b77b4be50de1352ab4ff2691a1a7afd8c1341475b4170ac50455973b7fcf3c24324fa9'   # noqa
_DEVICE_VERIFY_STEP2 = b'00000000a1f91acf64aacb185684080b817103b423816ad63b7f5e001f62337b4cc4b3b92c1474959930b7c2a59d0004814300580459d06fc6cc6441bd82bac72a5c5cc7'  # noqa
_DEVICE_VERIFY_STEP2_RESP = b''  # Value not used by pyatv

# pylint: enable=E501
# --- END AUTHENTICATION DATA ---

LoginResponse = namedtuple('LoginResponse', 'session, status')
ArtworkResponse = namedtuple('ArtworkResponse', 'content, status')
AirPlayPlaybackResponse = namedtuple('AirPlayPlaybackResponse', 'content')
PairingResponse = namedtuple('PairingResponse', 'remote_name, pairing_code')


class PlayingResponse:
    """Response returned by command playstatusupdate."""

    def __init__(self, revision=0, shuffle=False, **kwargs):
        """Initialize a new PlayingResponse."""
        self.paused = self._get('paused', **kwargs)
        self.title = self._get('title', **kwargs)
        self.artist = self._get('artist', **kwargs)
        self.album = self._get('album', **kwargs)
        self.total_time = self._get('total_time', **kwargs)
        self.position = self._get('position', **kwargs)
        self.mediakind = self._get('mediakind', **kwargs)
        self.playstatus = self._get('playstatus', **kwargs)
        self.repeat = self._get('repeat', **kwargs)
        self.revision = revision
        self.shuffle = shuffle

    def _get(self, name, **kwargs):
        if name in kwargs:
            return kwargs[name]
        else:
            return None


class FakeAppleTV(web.Application):
    """Implementation of fake Apple TV."""

    def __init__(self, loop, hsgid, pairing_guid, session_id, testcase):
        """Initialize a new FakeAppleTV."""
        super().__init__()
        self.responses = {}
        self.responses['login'] = [LoginResponse(session_id, 200)]
        self.responses['artwork'] = []
        self.responses['playing'] = []
        self.responses['airplay_playback'] = []
        self.responses['pairing'] = []
        self.hsgid = hsgid
        self.pairing_guid = pairing_guid
        self.session = None
        self.last_button_pressed = None
        self.buttons_press_count = 0
        self.has_authenticated = True
        self.last_airplay_url = None
        self.properties = {}  # setproperty
        self.tc = testcase

        # Regular DAAP stuff
        self.router.add_get('/login', self.handle_login)
        self.router.add_get(
            '/ctrl-int/1/playstatusupdate', self.handle_playstatus)
        self.router.add_post(
            '/ctrl-int/1/controlpromptentry', self.handle_remote_button)
        self.router.add_get(
            '/ctrl-int/1/nowplayingartwork', self.handle_artwork)
        self.router.add_post(
            '/ctrl-int/1/setproperty', self.handle_set_property)
        for button in ['play', 'pause', 'stop', 'nextitem', 'previtem']:
            self.router.add_post('/ctrl-int/1/' + button,
                                 self.handle_playback_button)

        # AirPlay stuff
        self.router.add_post('/play', self.handle_airplay_play)
        self.router.add_get('/playback-info',
                            self.handle_airplay_playback_info)
        self.router.add_post('/pair-pin-start',
                             self.handle_pair_pin_start)
        self.router.add_post('/pair-setup-pin',
                             self.handle_pair_setup_pin)
        self.router.add_post('/pair-verify',
                             self.handle_airplay_pair_verify)

    # This method will retrieve the next response for a certain type.
    # If there are more than one response, it "pop" the last one and
    # return it. When only one response remains, that response will be
    # kept and returned for all further calls.
    def _get_response(self, response_name, pop=True):
        responses = self.responses[response_name]
        if len(responses) == 0:
            return None
        elif len(responses) == 1:
            return responses[0]
        elif pop:
            return responses.pop()
        return responses[len(responses)-1]

    @asyncio.coroutine
    def handle_login(self, request):
        """Handle login requests."""
        self._verify_headers(request)
        self._verify_auth_parameters(
            request, check_login_id=True, check_session=False)

        data = self._get_response('login')
        mlid = tags.uint32_tag('mlid', data.session)
        mlog = tags.container_tag('mlog', mlid)
        self.session = data.session
        return web.Response(body=mlog, status=data.status)

    @asyncio.coroutine
    def handle_playback_button(self, request):
        """Handle playback buttons."""
        self._verify_auth_parameters(request)
        self.last_button_pressed = request.rel_url.path.split('/')[-1]
        self.buttons_press_count += 1
        return web.Response(status=200)

    @asyncio.coroutine
    def handle_remote_button(self, request):
        """Handle remote control buttons."""
        self._verify_auth_parameters(request)
        content = yield from request.content.read()
        parsed = dmap.parse(content, tag_definitions.lookup_tag)
        self.last_button_pressed = self._convert_button(parsed)
        self.buttons_press_count += 1
        return web.Response(status=200)

    @staticmethod
    def _convert_button(data):
        value = dmap.first(data, 'cmbe')
        if value == 'touchUp&time=6&point=20,250':
            return 'up'
        elif value == 'touchUp&time=6&point=20,275':
            return 'down'
        elif value == 'touchUp&time=7&point=50,100':
            return 'left'
        elif value == 'touchUp&time=7&point=75,100':
            return 'right'
        else:
            return value

    @asyncio.coroutine
    def handle_artwork(self, request):
        """Handle artwork requests."""
        self._verify_auth_parameters(request)
        artwork = self._get_response('artwork')
        return web.Response(body=artwork.content, status=artwork.status)

    @asyncio.coroutine
    def handle_playstatus(self, request):
        """Handle  playstatus (currently playing) requests."""
        self._verify_auth_parameters(request)

        body = b''
        playing = self._get_response('playing')

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

        if playing.total_time is not None:
            total_time = playing.total_time * 1000  # sec -> ms
            body += tags.uint32_tag('cast', total_time)

            if playing.position is not None:
                pos = (playing.total_time - playing.position)
                body += tags.uint32_tag('cant', pos*1000)  # sec -> ms

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

    @asyncio.coroutine
    def handle_set_property(self, request):
        """Handle property changes."""
        self._verify_auth_parameters(request)
        if 'dacp.playingtime' in request.rel_url.query:
            self.properties['dacp.playingtime'] = int(
                request.rel_url.query['dacp.playingtime'])
        elif 'dacp.shufflestate' in request.rel_url.query:
            self.properties['dacp.shufflestate'] = int(
                request.rel_url.query['dacp.shufflestate'])
        elif 'dacp.repeatstate' in request.rel_url.query:
            self.properties['dacp.repeatstate'] = int(
                request.rel_url.query['dacp.repeatstate'])
        else:
            web.Response(body=b'', status=500)

        return web.Response(body=b'', status=200)

    @asyncio.coroutine
    def trigger_bonjour(self, stubbed_zeroconf):
        """Act upon available Bonjour services."""
        # Add more services here when needed
        for service in stubbed_zeroconf.registered_services:
            if service.type != '_touch-remote._tcp.local.':
                continue

            # Look for the response matching this remote
            remote_name = service.properties[b'DvNm']
            for response in self.responses['pairing']:
                if response.remote_name == remote_name:
                    return self.perform_pairing(response, service.port)

    @asyncio.coroutine
    def perform_pairing(self, pairing_response, port):
        """Pair with a remote client.

        This will perform a GET-request to the specified port and hand over
        information to the client (pyatv) so that the pairing process can be
        completed.
        """
        server = 'http://127.0.0.1:{}'.format(port)
        url = '{}/pairing?pairingcode={}&servicename=test'.format(
            server, pairing_response.pairing_code)
        data, _ = yield from utils.simple_get(url, self.loop)

        # Verify content returned in pairingresponse
        parsed = dmap.parse(data, tag_definitions.lookup_tag)
        self.tc.assertEqual(dmap.first(parsed, 'cmpa', 'cmpg'), 1)
        self.tc.assertEqual(dmap.first(parsed, 'cmpa', 'cmnm'),
                            pairing_response.remote_name)
        self.tc.assertEqual(dmap.first(parsed, 'cmpa', 'cmty'), 'ipod')

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

    @asyncio.coroutine
    def handle_airplay_play(self, request):
        """Handle AirPlay play requests."""
        if not self.has_authenticated:
            return web.Response(status=503)

        headers = request.headers

        # Verify headers first
        self.tc.assertEqual(headers['User-Agent'], 'MediaControl/1.0')
        self.tc.assertEqual(headers['Content-Type'], 'text/parameters')

        body = yield from request.text()

        self.last_airplay_url = re.search(
            r'Content-Location: (.*)', body).group(1)
        self.last_airplay_start = float(re.search(
            r'Start-Position: (.*)', body).group(1))

        return web.Response(status=200)

    def handle_airplay_playback_info(self, request):
        """Handle AirPlay playback-info requests."""
        response = self._get_response('airplay_playback')
        return web.Response(body=response.content, status=200)

    # TODO: Extract device auth code to separate module and make it more
    # general. This is a dumb implementation that verifies hard coded values,
    # which is fine for regression but an implementation with better validation
    # would be better.
    def handle_pair_pin_start(self, request):
        """Handle start of AirPlay device authentication."""
        return web.Response(status=200)  # Normally never fails

    def handle_pair_setup_pin(self, request):
        """Handle AirPlay device authentication requests."""
        content = yield from request.content.read()
        hexlified = binascii.hexlify(content)

        if hexlified == _DEVICE_AUTH_STEP1:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_AUTH_STEP1_RESP), status=200)
        elif hexlified == _DEVICE_AUTH_STEP2:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_AUTH_STEP2_RESP), status=200)
        elif hexlified == _DEVICE_AUTH_STEP3:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_AUTH_STEP3_RESP), status=200)

        return web.Response(status=503)

    def handle_airplay_pair_verify(self, request):
        """Handle verification of AirPlay device authentication."""
        content = yield from request.content.read()
        hexlified = binascii.hexlify(content)

        if hexlified == _DEVICE_VERIFY_STEP1:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_VERIFY_STEP1_RESP), status=200)
        elif hexlified == _DEVICE_VERIFY_STEP2:
            self.has_authenticated = True
            return web.Response(body=_DEVICE_VERIFY_STEP2_RESP, status=200)

        return web.Response(body=b'', status=503)


class AppleTVUseCases:
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

    def change_artwork(self, artwork):
        """Call this method to change artwork response."""
        self.device.responses['artwork'].insert(
            0, ArtworkResponse(artwork, 200))

    def artwork_no_permission(self):
        """Make artwork fail with no permission.

        This corresponds to have been logged out for some reason.
        """
        self.device.responses['artwork'].insert(
            0, ArtworkResponse(None, 403))

    def nothing_playing(self):
        """Call this method to put device in idle state."""
        self.device.responses['playing'].insert(0, PlayingResponse())

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
            shuffle = kwargs['shuffle']
        if 'repeat' in kwargs:
            repeat = kwargs['repeat']
        self.device.responses['playing'].insert(0, PlayingResponse(
            revision=revision,
            paused=paused, title=title,
            total_time=total_time, position=position,
            mediakind=3, shuffle=shuffle, repeat=repeat))

    def music_playing(self, paused, artist, album, title,
                      total_time, position):
        """Call this method to change what is currently plaing to music."""
        self.device.responses['playing'].insert(0, PlayingResponse(
            paused=paused, title=title,
            artist=artist, album=album,
            total_time=total_time,
            position=position,
            mediakind=2))

    def media_is_loading(self):
        """Call this method to put device in a loading state."""
        self.device.responses['playing'].insert(0, PlayingResponse(
            playstatus=1))

    def airplay_playback_idle(self):
        """Make playback-info return idle info."""
        plist = dict(readyToPlay=False, uuid=123)
        self.device.responses['airplay_playback'].insert(
            0, AirPlayPlaybackResponse(plistlib.dumps(plist)))

    def set_property(self, prop, value):
        """Change value of a property."""
        # Use "fictional" properties to not tie them to DAP (if some other
        # protocol is to be supported in the future)
        if prop == 'shuffle':
            self.device.properties['dacp.shufflestate'] = value
        elif prop == 'repeat':
            self.device.properties['dacp.repeatstate'] = value

    def airplay_playback_playing(self):
        """Make playback-info return that something is playing."""
        # This is _not_ complete, currently not needed
        plist = dict(duration=0.8)
        self.device.responses['airplay_playback'].insert(
            0, AirPlayPlaybackResponse(plistlib.dumps(plist)))

    def airplay_require_authentication(self):
        """Require device authentication for AirPlay."""
        self.device.has_authenticated = False

    def pairing_response(self, remote_name, expected_pairing_code):
        """Reponse when a pairing request is made."""
        self.device.responses['pairing'].insert(0, PairingResponse(
            remote_name, expected_pairing_code))

    @asyncio.coroutine
    def act_on_bonjour_services(self, stubbed_zeroconf):
        """Act on available Bonjour services.

        This will make the device look at published services and perform
        actions base on these. Most imporant for the pairing process.
        """
        yield from self.device.trigger_bonjour(stubbed_zeroconf)
