"""API exposed by the library."""

import re
import inspect

from abc import (ABCMeta, abstractmethod, abstractproperty)

from pyatv import (convert, exceptions)


# TODO: make these methods more pretty and safe
def _get_first_sentence_in_pydoc(obj):
    doc = obj.__doc__
    index = doc.find('.')
    if index == -1:
        # Here we have no leading . so return everything
        return doc
    else:
        # Try to find the first complete sentence and respect
        # abbreviations correctly
        match = re.findall(r'(.*\.[^A-Z]*)\.(?: [A-Z].*|)', doc)
        if len(match) == 1:
            return match[0]
        else:
            return doc[0:index]


def retrieve_commands(obj, developer=False):
    """Retrieve all commands and help texts from an API object."""
    commands = {}  # Name and help
    for member in [obj]+obj.__class__.mro():
        for func in member.__dict__:
            if not inspect.isfunction(member.__dict__[func]) and \
               not isinstance(member.__dict__[func], property):
                continue
            if func.startswith('_'):
                continue
            if func.startswith('dev_') and not developer:
                continue
            commands[func] = _get_first_sentence_in_pydoc(
                member.__dict__[func])
    return commands


class RemoteControl(object):
    """Base class for API used to control an Apple TV."""

    __metaclass__ = ABCMeta

    # pylint: disable=invalid-name
    @abstractmethod
    def up(self):
        """Press key up."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def down(self):
        """Press key down."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def left(self):
        """Press key left."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def right(self):
        """Press key right."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def play(self):
        """Press key play."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def pause(self):
        """Press key play."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def next(self):
        """Press key next."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def previous(self):
        """Press key previous."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def select(self):
        """Press key select."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def menu(self):
        """Press key menu."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def top_menu(self):
        """Go to main menu (long press menu)."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def set_position(self, pos):
        """Seek in the current playing media."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def play_url(self, url, start_position=0, port=7000):
        """Play media from an URL on the device."""
        raise exceptions.NotSupportedError


class Playing(object):
    """Base class for retrieving what is currently playing."""

    __metaclass__ = ABCMeta

    def __str__(self):
        """Convert this playing object to a readable string."""
        output = []
        output.append('Media type: {0}'.format(
            convert.media_type_str(self.media_type)))
        output.append('Play state: {0}'.format(
            convert.playstate_str(self.play_state)))

        if self.title is not None:
            output.append('     Title: {0}'.format(self.title))

        if self.artist is not None:
            output.append('    Artist: {0}'.format(self.artist))

        if self.album is not None:
            output.append('     Album: {0}'.format(self.album))

        position = self.position
        total_time = self.total_time
        if position is not None and total_time is not None and total_time != 0:
            output.append('  Position: {0}/{1}s ({2:.1%})'.format(
                position, total_time, float(position)/float(total_time)))
        elif position is not None and position != 0:
            output.append('  Position: {0}s'.format(position))
        elif total_time is not None and position != 0:
            output.append('Total time: {0}s'.format(total_time))

        return '\n'.join(output)

    @abstractproperty
    def media_type(self):
        """What type of media is currently playing, e.g. video, music."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def play_state(self):
        """Current play state, e.g. playing or paused."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def title(self):
        """Title of the current media, e.g. movie or song name."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def artist(self):
        """Artist of the currently playing song."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def album(self):
        """Album of the currently playing song."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def total_time(self):
        """Total play time in seconds."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def position(self):
        """Current position in the playing media (seconds)."""
        raise exceptions.NotSupportedError


# pylint: disable=too-few-public-methods
class Metadata(object):
    """Base class for retrieving metadata from an Apple TV."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def artwork(self):
        """Return artwork for what is currently playing (or None)."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def artwork_url(self):
        """Return artwork URL for what is currently playing."""
        raise exceptions.NotSupportedError

    @abstractmethod
    def playing(self):
        """Return what is currently playing."""
        raise exceptions.NotSupportedError


class PushUpdater(object):
    """Base class for push/async updates from an Apple TV."""

    __metaclass__ = ABCMeta

    @property
    def listener(self):
        """Listener (PushUpdaterListener) that receives updates."""
        raise exceptions.NotSupportedError

    @listener.setter  # type: ignore
    @abstractmethod
    def listener(self, listener):
        """Listener that receives updates.

        This should be an object implementing two methods:
        - playstatus_update(updater, playstatus)
        - playstatus_error(updater, exception)

        The first method is called when a new update happens and the second one
        is called if an error occurs. Please not that if an error happens, push
        updates will be stopped. So they will need to be enabled again, e.g.
        from the error method. A delay should preferably be passed to start()
        to avoid an infinite error-loop.
        """
        raise exceptions.NotSupportedError

    @abstractmethod
    def start(self, initial_delay=0):
        """Begin to listen to updates.

        If an error occurs, start must be called again.
        """
        raise exceptions.NotSupportedError

    @abstractmethod
    def stop(self):
        """No longer listen for updates."""
        raise exceptions.NotSupportedError


class AppleTV(object):
    """Base class representing an Apple TV."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def login(self):
        """Perform an explicit login.

        Not needed as login is performed automatically.
        """
        raise exceptions.NotSupportedError

    @abstractmethod
    def logout(self):
        """Perform an explicit logout.

        Must be done when session is no longer needed to not leak resources.
        """
        raise exceptions.NotSupportedError

    @abstractproperty
    def remote_control(self):
        """Return API for controlling the Apple TV."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def metadata(self):
        """Return API for retrieving metadata from the Apple TV."""
        raise exceptions.NotSupportedError

    @abstractproperty
    def push_updater(self):
        """Return API for handling push update from the Apple TV."""
        raise exceptions.NotSupportedError
