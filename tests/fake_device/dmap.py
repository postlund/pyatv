"""Fake DMAP Apple TV device for tests."""

from collections import namedtuple
import logging
import math

from aiohttp import web

from pyatv.const import InputAction, RepeatState, ShuffleState
from pyatv.protocols.dmap import parser, tag_definitions, tags
from pyatv.support.net import unused_port

from tests import utils

_LOGGER = logging.getLogger(__name__)

EXPECTED_HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip",
    "Client-DAAP-Version": "3.13",
    "Client-ATV-Sharing-Version": "1.2",
    "Client-iTunes-Sharing-Version": "3.15",
    "User-Agent": "Remote/1021",
    "Viewer-Only-Client": "1",
}

LoginResponse = namedtuple("LoginResponse", "session, status")
AirPlayPlaybackResponse = namedtuple("AirPlayPlaybackResponse", "content")


DEVICE_IDENTIFIER = "75FBEEC773CFC563"
DEVICE_AUTH_KEY = "8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493"
DEVICE_PIN = 2271
DEVICE_CREDENTIALS = DEVICE_IDENTIFIER + ":" + DEVICE_AUTH_KEY


class PlayingResponse:
    """Response returned by command playstatusupdate."""

    def __init__(self, revision=0, **kwargs):
        """Initialize a new PlayingResponse."""
        self.paused = kwargs.get("paused")
        self.title = kwargs.get("title")
        self.artist = kwargs.get("artist")
        self.album = kwargs.get("album")
        self.genre = kwargs.get("genre")
        self.total_time = kwargs.get("total_time")
        self.position = kwargs.get("position")
        self.mediakind = kwargs.get("mediakind")
        self.playstatus = kwargs.get("playstatus")
        self.repeat = kwargs.get("repeat")
        self.playback_rate = kwargs.get("playback_rate")
        self.revision = revision
        self.shuffle = kwargs.get("shuffle")
        self.force_close = kwargs.get("force_close", False)
        self.artwork = kwargs.get("artwork")
        self.artwork_status = kwargs.get("artwork_status")


class FakeDmapState:
    def __init__(self, hsgid, pairing_guid, session_id):
        self.device = None
        self.hsgid = hsgid
        self.pairing_guid = pairing_guid
        self.session_id = session_id
        self.login_response = LoginResponse(session_id, 200)
        self.playing = PlayingResponse()
        self.pairing_responses = {}  # Remote name -> expected code
        self.session = None
        self.volume_controls = False
        self.last_button_pressed = None
        self.last_button_action = None
        self.buttons_press_count = 0
        self.last_artwork_width = None
        self.last_artwork_height = None

    async def trigger_bonjour(self, stubbed_zeroconf):
        """Act upon available Bonjour services."""
        # Add more services here when needed
        for service in stubbed_zeroconf.registered_services:
            if service.type != "_touch-remote._tcp.local.":
                continue

            # Look for the response matching this remote
            remote_name = service.properties["DvNm"]
            for remote_name, expected_code in self.pairing_responses.items():
                if remote_name == remote_name:
                    return await self.perform_pairing(
                        remote_name, expected_code, service.port
                    )

    async def perform_pairing(self, remote_name, expected_code, port):
        """Pair with a remote client.

        This will perform a GET-request to the specified port and hand over
        information to the client (pyatv) so that the pairing process can be
        completed.
        """
        server = f"http://127.0.0.1:{port}"
        url = f"{server}/pair?pairingcode={expected_code}&servicename=test"
        data, _ = await utils.simple_get(url)

        # Verify content returned in pairingresponse
        parsed = parser.parse(data, tag_definitions.lookup_tag)
        assert parser.first(parsed, "cmpa", "cmpg") == 1
        assert parser.first(parsed, "cmpa", "cmnm") == remote_name
        assert parser.first(parsed, "cmpa", "cmty") == "iPhone"


class FakeDmapService:
    """Implementation of a fake DMAP Apple TV."""

    def __init__(self, state, app, loop):
        """Initialize a new FakeAppleTV."""
        self.state = state
        self.port = None
        self.app = app
        self.runner = None

        self.app.router.add_get("/login", self.handle_login)
        self.app.router.add_get("/ctrl-int/1/playstatusupdate", self.handle_playstatus)
        self.app.router.add_post(
            "/ctrl-int/1/controlpromptentry", self.handle_remote_button
        )
        self.app.router.add_get("/ctrl-int/1/nowplayingartwork", self.handle_artwork)
        self.app.router.add_post("/ctrl-int/1/setproperty", self.handle_set_property)
        for button in [
            "play",
            "playpause",
            "pause",
            "stop",
            "nextitem",
            "previtem",
            "volumedown",
            "volumeup",
        ]:
            self.app.router.add_post(
                "/ctrl-int/1/" + button, self.handle_playback_button
            )

    async def start(self, start_web_server: bool):
        if start_web_server:
            self.port = unused_port()
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await site.start()

    async def cleanup(self):
        if self.runner:
            await self.runner.cleanup()

    async def handle_login(self, request):
        """Handle login requests."""
        self._verify_headers(request)
        self._verify_auth_parameters(request, check_login_id=True, check_session=False)

        mlid = tags.uint32_tag("mlid", self.state.login_response.session)
        mlog = tags.container_tag("mlog", mlid)
        self.state.session = self.state.login_response.session
        return web.Response(body=mlog, status=self.state.login_response.status)

    async def handle_playback_button(self, request):
        """Handle playback buttons."""
        self._verify_auth_parameters(request)
        self.state.last_button_pressed = request.rel_url.path.split("/")[-1]
        self.state.last_button_action = None
        self.state.buttons_press_count += 1
        return web.Response(status=200)

    async def handle_remote_button(self, request):
        """Handle remote control buttons."""
        self._verify_auth_parameters(request)
        content = await request.content.read()
        parsed = parser.parse(content, tag_definitions.lookup_tag)
        self.state.last_button_pressed = self._convert_button(parsed)
        self.state.last_button_action = InputAction.SingleTap
        self.state.buttons_press_count += 1
        return web.Response(status=200)

    def _convert_button(self, data):
        value = parser.first(data, "cmbe")

        # Consider navigation buttons if six commands have been received
        if self.state.buttons_press_count == 6:
            if value == "touchUp&time=6&point=20,250":
                return "up"
            elif value == "touchUp&time=6&point=20,275":
                return "down"
            elif value == "touchUp&time=7&point=50,100":
                return "left"
            elif value == "touchUp&time=7&point=75,100":
                return "right"

        return value

    async def handle_artwork(self, request):
        """Handle artwork requests."""
        self._verify_auth_parameters(request)

        if "mh" in request.query:
            self.state.last_artwork_height = int(request.query.get("mh"))

        if "mw" in request.query:
            self.state.last_artwork_width = int(request.query.get("mw"))

        return web.Response(
            body=self.state.playing.artwork, status=self.state.playing.artwork_status
        )

    async def handle_playstatus(self, request):
        """Handle  playstatus (currently playing) requests."""
        self._verify_auth_parameters(request)

        body = b""
        playing = self.state.playing

        # Check if connection should be closed to trigger error on client side
        if playing.force_close:
            await request.transport.close()

        # Make sure revision matches
        revision = int(request.rel_url.query["revision-number"])
        if playing.revision != revision:
            # Not a valid response as a real device, just to make tests fail
            return web.Response(status=500)

        if playing.playback_rate is not None:
            # TODO : Magic constants
            if math.isclose(playing.playback_rate, 0.0):
                playstatus = 3
            elif math.isclose(playing.playback_rate, 1.0):
                playstatus = 4
            elif playing.playback_rate > 0.0:
                playstatus = 6
            else:
                playstatus = 5
            body += tags.uint32_tag("caps", playstatus)
        elif playing.paused is not None:
            body += tags.uint32_tag("caps", 3 if playing.paused else 4)
        elif playing.playstatus is not None:
            body += tags.uint32_tag("caps", playing.playstatus)

        if playing.title is not None:
            body += tags.string_tag("cann", playing.title)

        if playing.artist is not None:
            body += tags.string_tag("cana", playing.artist)

        if playing.album is not None:
            body += tags.string_tag("canl", playing.album)

        if playing.genre is not None:
            body += tags.string_tag("cang", playing.genre)

        if playing.total_time is not None:
            total_time = playing.total_time * 1000  # sec -> ms
            body += tags.uint32_tag("cast", total_time)

            if playing.position is not None:
                pos = playing.total_time - playing.position
                body += tags.uint32_tag("cant", pos * 1000)  # sec -> ms

        if playing.mediakind is not None:
            body += tags.uint32_tag("cmmk", playing.mediakind)

        if playing.repeat is not None:
            body += tags.uint8_tag("carp", playing.repeat.value)

        if playing.shuffle is not None:
            body += tags.uint8_tag("cash", playing.shuffle.value)

        if self.state.volume_controls is not None:
            body += tags.uint8_tag("cavc", self.state.volume_controls)

        body += tags.uint32_tag("cmsr", playing.revision + 1)

        return web.Response(body=tags.container_tag("cmst", body), status=200)

    async def handle_set_property(self, request):
        """Handle property changes."""
        self._verify_auth_parameters(request)
        if "dacp.playingtime" in request.rel_url.query:
            playtime = int(request.rel_url.query["dacp.playingtime"])
            self.state.playing.position = int(playtime / 1000)
        elif "dacp.shufflestate" in request.rel_url.query:
            shuffle = int(request.rel_url.query["dacp.shufflestate"])
            self.state.playing.shuffle = (
                ShuffleState.Songs if shuffle == 1 else ShuffleState.Off
            )
        elif "dacp.repeatstate" in request.rel_url.query:
            repeat = int(request.rel_url.query["dacp.repeatstate"])
            self.state.playing.repeat = RepeatState(repeat)
        else:
            web.Response(body=b"", status=500)

        return web.Response(body=b"", status=200)

    # Verifies that all needed headers are included in the request. Should be
    # checked in all requests, but that seems a bit too much and not that
    # necessary.
    def _verify_headers(self, request):
        for header in EXPECTED_HEADERS:
            assert header in request.headers
            assert request.headers[header] == EXPECTED_HEADERS[header]

    # This method makes sure that the correct login id and/or session id is
    # included in the GET-parameters. As this is extremely important for
    # anything to work, this should be verified in all requests.
    def _verify_auth_parameters(
        self, request, check_login_id=False, check_session=True
    ):
        params = request.rel_url.query

        # Either hsgid or pairing-guid should be present
        if check_login_id:
            if "hsgid" in params:
                assert params["hsgid"] == self.state.hsgid, "hsgid does not match"
            elif "pairing-guid" in params:
                assert (
                    params["pairing-guid"] == self.state.pairing_guid
                ), "pairing-guid does not match"
            else:
                assert False, "hsgid or pairing-guid not found"

        if check_session:
            assert (
                int(params["session-id"]) == self.state.session
            ), "session id does not match"


class FakeDmapUseCases:
    """Wrapper for altering behavior of a FakeAppleTV instance.

    Extend and use this class to alter behavior of a fake Apple TV device.
    """

    def __init__(self, state):
        """Initialize a new AppleTVUseCases."""
        self.state = state

    def change_volume_control(self, available):
        """Change volume control availability."""
        self.state.volume_controls = available

    def force_relogin(self, session):
        """Call this method to change current session id."""
        self.state.login_response = LoginResponse(session, 200)

    def make_login_fail(self):
        """Call this method to make login fail with response 503."""
        self.state.login_response = LoginResponse(0, 503)

    def change_artwork(
        self, artwork, mimetype, identifier=None, width=None, height=None
    ):
        """Call this method to change artwork response."""
        self.state.playing.artwork = artwork
        self.state.playing.artwork_status = 200

    def artwork_no_permission(self):
        """Make artwork fail with no permission.

        This corresponds to have been logged out for some reason.
        """
        self.state.playing.artwork = None
        self.state.playing.artwork_status = 403

    def nothing_playing(self):
        """Call this method to put device in idle state."""
        self.state.playing = PlayingResponse()

    def server_closes_connection(self):
        """Call this method to force server to close connection on request."""
        self.state.playing = PlayingResponse(force_close=True)

    def example_video(self, paused=True, **kwargs):
        """Play some example video."""
        kwargs.setdefault("title", "dummy")
        kwargs.setdefault("paused", True)
        self.video_playing(total_time=123, position=3, **kwargs)

    def video_playing(self, paused, title, total_time, position, **kwargs):
        """Call this method to change what is currently plaing to video."""
        revision = 0
        shuffle = None
        repeat = None
        playback_rate = kwargs.get("playback_rate", None)
        if "revision" in kwargs:
            revision = kwargs["revision"]
        if "shuffle" in kwargs:
            shuffle = kwargs["shuffle"]
        if "repeat" in kwargs:
            repeat = kwargs["repeat"]
        self.state.playing = PlayingResponse(
            revision=revision,
            paused=paused,
            title=title,
            total_time=total_time,
            position=position,
            mediakind=3,
            shuffle=shuffle,
            repeat=repeat,
            playback_rate=playback_rate,
        )

    def example_music(self, **kwargs):
        """Play some example music."""
        kwargs.setdefault("paused", True)
        kwargs.setdefault("title", "music")
        kwargs.setdefault("artist", "artist")
        kwargs.setdefault("album", "album")
        kwargs.setdefault("total_time", 49)
        kwargs.setdefault("position", 22)
        kwargs.setdefault("genre", "genre")
        self.music_playing(**kwargs)

    def music_playing(
        self, paused, artist, album, title, genre, total_time, position, **kwargs
    ):
        """Call this method to change what is currently playing to music."""
        self.state.playing = PlayingResponse(
            paused=paused,
            title=title,
            artist=artist,
            album=album,
            total_time=total_time,
            position=position,
            genre=genre,
            mediakind=2,
            **kwargs,
        )

    def media_is_loading(self):
        """Call this method to put device in a loading state."""
        self.state.playing = PlayingResponse(playstatus=1)

    def pairing_response(self, remote_name, expected_pairing_code):
        """Response when a pairing request is made."""
        self.state.pairing_responses[remote_name] = expected_pairing_code

    async def act_on_bonjour_services(self, stubbed_zeroconf):
        """Act on available Bonjour services.

        This will make the device look at published services and perform
        actions base on these. Most important for the pairing process.
        """
        await self.state.trigger_bonjour(stubbed_zeroconf)
