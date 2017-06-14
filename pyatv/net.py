"""Methods used to make GET/POST requests."""

import logging
import asyncio
import binascii

_LOGGER = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 10.0  # Seconds


class HttpSession(object):
    """This class simplifies GET/POST requests."""

    def __init__(self, client_session, base_url):
        """Initialize a new HttpSession."""
        self._session = client_session  # aiohttp session
        self.base_url = base_url

    @asyncio.coroutine
    def get_data(self, path, headers=None, timeout=None):
        """Perform a GET request."""
        url = self.base_url + path
        _LOGGER.debug('GET URL: %s', url)
        resp = None
        try:
            resp = yield from self._session.get(
                url, headers=headers,
                timeout=DEFAULT_TIMEOUT if timeout is None else timeout)
            if resp.content_length is not None:
                resp_data = yield from resp.read()
            else:
                resp_data = None
            return resp_data, resp.status
        except Exception as ex:
            if resp is not None:
                resp.close()
            raise ex
        finally:
            if resp is not None:
                yield from resp.release()

    @asyncio.coroutine
    def post_data(self, path, data=None, headers=None, timeout=None):
        """Perform a POST request."""
        url = self.base_url + path
        _LOGGER.debug('POST URL: %s', url)
        self._log_data(data, False)

        resp = None
        try:
            resp = yield from self._session.post(
                url, headers=headers, data=data,
                timeout=DEFAULT_TIMEOUT if timeout is None else timeout)
            if resp.content_length is not None:
                resp_data = yield from resp.read()
            else:
                resp_data = None
            self._log_data(resp_data, True)
            return resp_data, resp.status
        except Exception as ex:
            if resp is not None:
                resp.close()
            raise ex
        finally:
            if resp is not None:
                yield from resp.release()

    @staticmethod
    def _log_data(data, is_recv):
        if data and _LOGGER.isEnabledFor(logging.DEBUG):
            output = data[0:128]
            _LOGGER.debug('%s Data[%d]: %s%s',
                          '<-' if is_recv else '->',
                          len(data),
                          binascii.hexlify(output),
                          '...' if len(output) != len(data) else '')
