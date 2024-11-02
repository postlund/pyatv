"""Classes and functions for data buffering."""

from typing import Union

from pyatv.exceptions import InvalidStateError

# Default values for buffer
BUFFER_SIZE = 8192
HEADROOM_SIZE = 1024


# This class could potentially be heavily optimized using memoryview (or bitarray). But
# kept simple for now.
class SemiSeekableBuffer:
    """Implementation of a "semi-seekable" buffer.

    A semi-seekable buffer in this context is a buffer that allows seeking, but with
    restrictions. The buffer shall be thought of more like a stream, where data is read
    in a stream like fashion but added similarly to like a buffer. The buffer has a
    fixed size internally, but an absolute "position" is maintained based on all data
    read from the buffer.

    To allow seeking, a "headroom" (with adjustable size) is kept in the beginning of
    the buffer. Data in the headroom is kept (internally) until the last byte of the
    headroom is read, after which is discarded from the internal buffer (and new data
    can be added again, in case buffer was full). As long as headroom is available,
    seeking is possible. But once it has been discarded, it is not. In analogy to a
    stream, this basically means the first X bytes of the stream is buffered and
    seekable until all X bytes have been read completely.

    The purpose of this kind of buffer is to support data streams (e.g. audio files)
    containing non-linear header data. Some file formats require "looking ahead" in the
    data stream to figure out the structure, thus seeking is needed to reset to
    beginning of the file. This is not a foolproof solution, but this allows for far
    better support in these cases.

    A special feature called "protected headroom" is also implemented. When enabled,
    the buffer acts as usual but the entire buffer is treated like headroom and no
    data is ever removed. This is particularly useful when reading metadata with one
    library (e.g. Mediafile) while decoding actual data with another library (e.g.
    miniaudio). In a non-seekable stream, the first library would consume data required
    by the second library. So you would get either metadata or audio data - but not
    both. By protecting the headroom, Mediafile can read data (and seek) as much as it
    wants, but it will always be possible to seek to the beginning again and remove
    the protection before passing buffer to miniaudio, thus allowing both metadata and
    audio data to be extracted properly.

    Protected headroom can only be enabled/disabled when position is 0, i.e. it
    cannot be enabled if data has been read nor can it be disabled before seeking to
    the beginning again.
    """

    def __init__(
        self,
        buffer_size: int = BUFFER_SIZE,
        /,
        seekable_headroom: int = HEADROOM_SIZE,
        protected_headroom: bool = False
    ) -> None:
        """Initialize a new SemiSeekableBuffer instance."""
        # Headroom cannot be smaller than actual buffer
        if seekable_headroom > buffer_size:
            raise ValueError("too large seekable headroom")

        self._buffer: bytes = b""
        self._buffer_size: int = buffer_size
        self._headroom: int = seekable_headroom
        self._position: int = 0
        self._has_headroom_data: bool = True
        self._protected: bool = protected_headroom

    def empty(self) -> bool:
        """Return True if buffer is empty, otherwise False."""
        return self.size == 0

    @property
    def size(self) -> int:
        """Return number of bytes in buffer."""
        return len(self._buffer) - (self._position if self._has_headroom_data else 0)

    @property
    def remaining(self) -> int:
        """Return remaining bytes in buffer."""
        return self._buffer_size - self.size

    @property
    def position(self) -> int:
        """Return absolute position of bytes read from buffer.

        This property reflects number of bytes returned by the get method in total. It
        is however reset in case of seeking to reflect seeking position (when
        possible).
        """
        return self._position

    @property
    def protected_headroom(self) -> bool:
        """Return if headroom is protected."""
        return self._protected

    @protected_headroom.setter
    def protected_headroom(self, protected: bool) -> None:
        """Set if headroom is protected or not."""
        if protected == self._protected:
            return

        if self.position != 0:
            raise InvalidStateError("not a starting position")

        self._protected = protected

    def add(self, data: bytes) -> int:
        """Add data to buffer.

        Returns number of bytes added to buffer.
        """
        room_in_buffer = min(len(data), self._buffer_size - len(self._buffer))
        self._buffer += data[0:room_in_buffer]
        return room_in_buffer

    def get(self, number_of_bytes: int) -> bytes:
        """Retrieve data from buffer.

        Will return b"" if buffer is empty.
        """
        # Use position as offset in case we have (potentially read but kept) headroom
        if self._has_headroom_data:
            data = self._buffer[self._position : self._position + number_of_bytes]
        else:
            data = self._buffer[0:number_of_bytes]

        self._position += len(data)

        # Treat entire buffer as headroom in case it's protected and do not remove
        # any data
        if not self.protected_headroom:
            if self._has_headroom_data:
                # If we read past the headroom, we shall discard it (and additional
                # data we read)
                if self._position >= self._headroom:
                    self._has_headroom_data = False
                    self._buffer = self._buffer[self._position :]
            else:
                self._buffer = self._buffer[len(data) :]

        return data

    def seek(self, position: int) -> bool:
        """Seek to absolute position in buffer.

        This method only works as long as there is headroom available. Returns True if
        seek was successful, otherwise False.
        """
        # This is a special case where we allow seeking to the current position
        if position == self.position:
            return True

        # Absolute position (i.e. total amount of data read from buffer) has passed
        # headroom space, so we have no headroom data and thus seeking not possible.
        if not self._has_headroom_data:
            return False

        # Can only seek within headroom
        if position >= self._headroom:
            return False

        # There must be data in buffer for seeking to work
        headroom_data_in_buffer = min(self._headroom, len(self._buffer))
        if position > (headroom_data_in_buffer - 1):
            return False

        self._position = position
        return True  # We have headroom data and position is within it

    def fits(self, data: Union[int, bytes]) -> bool:
        """Check if data (or amount of data) fits in the buffer.

        This method is purely for convenience.
        """
        in_size = len(data) if isinstance(data, bytes) else data
        return (len(self._buffer) + in_size) <= self._buffer_size

    def __len__(self) -> int:
        """Return number of bytes in buffer."""
        return self.size
