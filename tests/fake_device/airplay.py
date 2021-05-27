"""A fake AirPlay device."""

import binascii
from collections import namedtuple
import logging
import plistlib
from typing import Optional

from aiohttp import web

from pyatv.support.net import unused_port

from tests.utils import simple_get

_LOGGER = logging.getLogger(__name__)


# --- START AUTHENTICATION DATA VALID SESSION (FROM DEVICE) ---

DEVICE_IDENTIFIER = "75FBEEC773CFC563"
DEVICE_AUTH_KEY = "8F06696F2542D70DF59286C761695C485F815BE3D152849E1361282D46AB1493"
DEVICE_PIN = 2271
DEVICE_CREDENTIALS = DEVICE_IDENTIFIER + ":" + DEVICE_AUTH_KEY

# pylint: disable=E501
# For authentication
_DEVICE_AUTH_STEP1 = b"62706c6973743030d201020304566d6574686f6454757365725370696e5f101037354642454543373733434643353633080d14191d0000000000000101000000000000000500000000000000000000000000000030"  # noqa
_DEVICE_AUTH_STEP1_RESP = b"62706c6973743030d20102030452706b5473616c744f1101008817e16146c7d12b45e810b0bf190a4ccb25d9a20a8d0504d874daa8db5574c51c8b33703a95c00bdbe99c8c3745d1ef1b38e538edfd98e09ec029effe6f28b3b54a1bd41c28d8f33da6f5ac9327bfce9a66869dae645b5cbd2c6b8fbe14a30ad4f8598154f2ef7f4f52cee3e3042a69780463c26bbb764870eb1995b26a2a4ade05564836d788baf07469a143c410ea9d07a068eb790b2b0aa5b86c990636814e3fa1a899ceba1af45b211ca4bd3b5b66ffaf16051a4f851e120476054258f257b8521a068907ad5e9c7220d5cef9aa072dec9edb7ebf633cad4d52d105cf58440f17e236332b0b26539851a879e9ac8d3c2da4c590785468e590296d39d7374f1010fca6dcb6b83a7c716a692f806e9159540008000d001000150119000000000000020100000000000000050000000000000000000000000000012c"  # noqa
_DEVICE_AUTH_STEP2 = b"62706c6973743030d20102030452706b5570726f6f664f1101000819b6ba7feead4753809314e2b4c5db9109f737a0fc70b758342b6bbf536fae4e40cf94607588abb17c2076030cc00c2c1fa5fc3b3dfe8aa1ec2f23f74d917c0792fbf02f131377dfb8ae2a1656ceaa0a36bb3ab752586e1af17e1d5ef24ce083f3f9298d0be761f26c0d48af86510bf9aac7940cf90bff6bd214cf34b5536856c80f076cfbe06fd69af9d6a07a6d3ac580dfffc8a40b9730575a16c5046cd73321a944880dcf9fac952afc7ffd2d135e57ec208b11cef22b734f331ad4d8c9a737b588f7b30bd5210c65cae2ba0226f69ce7b505771faa63af89ed2f9e8325d7d5f3a2da7412f9d837860632d7f81b7fa5e09dd85e1539184070c0fa8433c24f1014fc6286910833d3e7ae0631d47ddbb0f492ef85b80008000d00100016011a0000000000000201000000000000000500000000000000000000000000000131"  # noqa
_DEVICE_AUTH_STEP2_RESP = b"62706c6973743030d101025570726f6f664f101484a88548b12bce122ad1cea6caff312630edcf27080b110000000000000101000000000000000300000000000000000000000000000028"  # noqa
_DEVICE_AUTH_STEP3 = b"62706c6973743030d20102030457617574685461675365706b4f101052a92f8712c6ea417f3adb3d03d8e5634f1020ff07fc8520d10728e6f2ab0a0245dfa20709b5d1ae5f9a19328b0663ba9414f2080d15192c000000000000010100000000000000050000000000000000000000000000004f"  # noqa
_DEVICE_AUTH_STEP3_RESP = b"62706c6973743030d2010203045365706b57617574685461674f10206285b20afad4cefe1fce40cee685ab072c75240cb47fb71bc3b3d03dca52dc5d4f1010893eb8e5ae418b245e9b1bf7cba9116b080d11193c000000000000010100000000000000050000000000000000000000000000004f"  # noqa

# For verification
_DEVICE_VERIFY_STEP1 = b"01000000891bae9f581f68f9c9933c4f713fbb5b9de639ec7df5d0a4fd4f342f1c21aa6a5e9d1e843302d6265b8c48dd169e273460e567916b0b36280ac071001118f6b2"  # noqa
_DEVICE_VERIFY_STEP1_RESP = b"3221371da9f00d035955caa912455fd2acee68117b557f25e39168746af4b631cfab7b2c6d0b58e96cc10af884f5a4cdef8063858a9d9c04e866743cf4b77b4be50de1352ab4ff2691a1a7afd8c1341475b4170ac50455973b7fcf3c24324fa9"  # noqa
_DEVICE_VERIFY_STEP2 = b"00000000a1f91acf64aacb185684080b817103b423816ad63b7f5e001f62337b4cc4b3b92c1474959930b7c2a59d0004814300580459d06fc6cc6441bd82bac72a5c5cc7"  # noqa
_DEVICE_VERIFY_STEP2_RESP = b""  # Value not used by pyatv

# pylint: enable=E501
# --- END AUTHENTICATION DATA ---

AirPlayPlaybackResponse = namedtuple("AirPlayPlaybackResponse", "code content")


class FakeAirPlayState:
    def __init__(self):
        self.airplay_responses = []
        self.has_authenticated = True
        self.always_auth_fail = False
        self.last_airplay_url = None
        self.last_airplay_start = None
        self.last_airplay_uuid = None
        self.last_airplay_content: Optional[bytes] = None
        self.play_count = 0
        self.injected_play_fails = 0


class FakeAirPlayService:
    def __init__(self, state, app, loop):
        self.state = state
        self.port = None
        self.app = app
        self.runner = None

        self.app.router.add_post("/play", self.handle_airplay_play)
        self.app.router.add_get("/playback-info", self.handle_airplay_playback_info)
        self.app.router.add_post("/pair-pin-start", self.handle_pair_pin_start)
        self.app.router.add_post("/pair-setup-pin", self.handle_pair_setup_pin)
        self.app.router.add_post("/pair-verify", self.handle_airplay_pair_verify)

    async def start(self, start_web_server):
        if start_web_server:
            self.port = unused_port()
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await site.start()

    async def cleanup(self):
        if self.runner:
            await self.runner.cleanup()

    async def handle_airplay_play(self, request):
        """Handle AirPlay play requests."""
        self.state.play_count += 1

        if self.state.always_auth_fail or not self.state.has_authenticated:
            return web.Response(status=503)
        if self.state.injected_play_fails > 0:
            self.state.injected_play_fails -= 1
            return web.Response(status=500)

        headers = request.headers

        # Verify headers first
        assert headers["User-Agent"] == "MediaControl/1.0"
        assert headers["Content-Type"] == "application/x-apple-binary-plist"

        body = await request.read()
        parsed = plistlib.loads(body)

        self.state.last_airplay_url = parsed["Content-Location"]
        self.state.last_airplay_start = parsed["Start-Position"]
        self.state.last_airplay_uuid = parsed["X-Apple-Session-ID"]

        # Simulate that fake device streams if URL is localhost
        if self.state.last_airplay_url.startswith("http://127.0.0.1"):
            _LOGGER.debug("Retrieving file from %s", self.state.last_airplay_url)
            self.state.last_airplay_content, _ = await simple_get(
                self.state.last_airplay_url
            )

        return web.Response(status=200)

    async def handle_airplay_playback_info(self, request):
        """Handle AirPlay playback-info requests."""
        if self.state.airplay_responses:
            response = self.state.airplay_responses.pop()
        else:
            plist = dict(readyToPlay=False, uuid=123)
            response = AirPlayPlaybackResponse(
                200, plistlib.dumps(plist).encode("utf-8")
            )
        return web.Response(
            body=response.content,
            status=response.code,
            content_type="text/x-apple-plist+xml",
        )

    # TODO: Extract device auth code to separate module and make it more
    # general. This is a dumb implementation that verifies hard coded values,
    # which is fine for regression but an implementation with better validation
    # would be better.
    async def handle_pair_pin_start(self, request):
        """Handle start of AirPlay device authentication."""
        return web.Response(status=200)  # Normally never fails

    async def handle_pair_setup_pin(self, request):
        """Handle AirPlay device authentication requests."""
        content = await request.content.read()
        hexlified = binascii.hexlify(content)

        if hexlified == _DEVICE_AUTH_STEP1:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_AUTH_STEP1_RESP), status=200
            )
        elif hexlified == _DEVICE_AUTH_STEP2:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_AUTH_STEP2_RESP), status=200
            )
        elif hexlified == _DEVICE_AUTH_STEP3:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_AUTH_STEP3_RESP), status=200
            )

        return web.Response(status=403)

    async def handle_airplay_pair_verify(self, request):
        """Handle verification of AirPlay device authentication."""
        content = await request.content.read()
        hexlified = binascii.hexlify(content)

        if hexlified == _DEVICE_VERIFY_STEP1:
            return web.Response(
                body=binascii.unhexlify(_DEVICE_VERIFY_STEP1_RESP), status=200
            )
        elif hexlified == _DEVICE_VERIFY_STEP2:
            self.state.has_authenticated = True
            return web.Response(body=_DEVICE_VERIFY_STEP2_RESP, status=200)

        return web.Response(body=b"", status=403)


class FakeAirPlayUseCases:
    """Wrapper for altering behavior of a FakeAirPlayDevice instance."""

    def __init__(self, state):
        """Initialize a new AirPlayUseCases."""
        self.state = state

    def airplay_play_failure(self, count):
        """Make play command fail a number of times."""
        self.state.injected_play_fails = count

    def airplay_playback_idle(self):
        """Make playback-info return idle info."""
        plist = dict(readyToPlay=False, uuid=123)
        self.state.airplay_responses.insert(
            0, AirPlayPlaybackResponse(200, plistlib.dumps(plist))
        )

    def airplay_playback_playing(self):
        """Make playback-info return that something is playing."""
        # This is _not_ complete, currently not needed
        plist = dict(duration=0.8)
        self.state.airplay_responses.insert(
            0, AirPlayPlaybackResponse(200, plistlib.dumps(plist))
        )

    def airplay_require_authentication(self):
        """Require device authentication for AirPlay."""
        self.state.has_authenticated = False

    def airplay_always_fail_authentication(self):
        """Always fail authentication for AirPlay."""
        self.state.always_auth_fail = True

    def airplay_playback_playing_no_permission(self):
        """Make playback-info return forbidden."""
        self.state.airplay_responses.insert(0, AirPlayPlaybackResponse(403, None))
