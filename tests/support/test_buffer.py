import pytest

from pyatv.exceptions import InvalidStateError
from pyatv.support import buffer as buf

BUFFER_SIZE = 5
HEADROOM = 2


@pytest.fixture(name="buffer")
def buffer_fixture() -> buf:
    yield buf.SemiSeekableBuffer(BUFFER_SIZE, seekable_headroom=0)


@pytest.fixture(name="headroom_buffer")
def buffer_headroom_fixture() -> buf:
    yield buf.SemiSeekableBuffer(BUFFER_SIZE, seekable_headroom=HEADROOM)


@pytest.fixture(name="protected")
def protected_fixture() -> buf:
    buffer = buf.SemiSeekableBuffer(BUFFER_SIZE, seekable_headroom=HEADROOM)
    buffer.protected_headroom = True
    yield buffer


def test_get_empty_buffer(buffer):
    assert buffer.get(1) == b""


def test_add_and_get(buffer):
    buffer.add(b"abc")
    assert buffer.get(1) == b"a"
    assert buffer.get(2) == b"bc"
    assert buffer.get(1) == b""


def test_add_until_full(buffer):
    assert buffer.add((BUFFER_SIZE - 1) * b"a") == BUFFER_SIZE - 1
    assert buffer.add(b"aa") == 1
    assert buffer.add(b"a") == 0


def test_buffer_size(buffer):
    assert buffer.size == 0

    buffer.add(b"a")
    assert buffer.size == 1
    assert len(buffer) == 1

    buffer.add(b"abc")
    assert buffer.size == 4
    assert len(buffer) == 4

    buffer.add(b"a" * (BUFFER_SIZE - 4))
    assert buffer.size == BUFFER_SIZE
    assert len(buffer) == BUFFER_SIZE

    buffer.add(b"a")
    assert buffer.size == BUFFER_SIZE
    assert len(buffer) == BUFFER_SIZE


def test_buffer_emptyness(buffer):
    assert buffer.empty()

    buffer.add(b"a")
    assert not buffer.empty()

    buffer.get(1)
    assert buffer.empty()


def test_buffer_remaining(buffer):
    assert buffer.remaining == BUFFER_SIZE

    buffer.add(b"a")
    assert buffer.remaining == BUFFER_SIZE - 1

    buffer.add(b"a" * BUFFER_SIZE)
    assert buffer.remaining == 0


def test_position_no_seeking(buffer):
    assert buffer.position == 0

    buffer.add(b"aaa")
    assert buffer.position == 0

    buffer.get(1)
    assert buffer.position == 1

    buffer.get(2)
    assert buffer.position == 3

    buffer.get(3)  # Buffer is empty at this point
    assert buffer.position == 3


def test_invalid_seekable_headroom():
    with pytest.raises(ValueError):
        buf.SemiSeekableBuffer(1, seekable_headroom=2)


def test_seek_outside_of_buffer(headroom_buffer):
    # Buffer is empty so should not be seekable
    assert not headroom_buffer.seek(1)


def test_simple_seek_within_headroom(headroom_buffer):
    headroom_buffer.add(b"aaaa")
    assert headroom_buffer.seek(1)
    assert not headroom_buffer.seek(2)
    assert headroom_buffer.seek(0)


def test_seek_outside_of_headroom_not_possible(headroom_buffer):
    headroom_buffer.add(BUFFER_SIZE * b"a")
    assert headroom_buffer.seek(HEADROOM - 1)
    assert not headroom_buffer.seek(HEADROOM)


def test_get_partial_data_allows_seeking(headroom_buffer):
    headroom_buffer.add(b"abcde")

    assert headroom_buffer.get(1) == b"a"
    assert headroom_buffer.size == 4
    assert headroom_buffer.position == 1

    headroom_buffer.seek(0)
    assert headroom_buffer.size == 5
    assert headroom_buffer.position == 0
    assert headroom_buffer.get(1) == b"a"
    assert headroom_buffer.size == 4
    assert headroom_buffer.position == 1


def test_get_all_headroom_disallows_seeking(headroom_buffer):
    headroom_buffer.add(b"abcde")

    assert headroom_buffer.get(2) == b"ab"
    assert not headroom_buffer.seek(0)
    assert headroom_buffer.size == 3
    assert headroom_buffer.position == 2


def test_can_add_after_headroom_is_removed(headroom_buffer):
    headroom_buffer.add(b"abcde")

    headroom_buffer.get(3)
    assert headroom_buffer.size == 2
    assert headroom_buffer.position == 3

    headroom_buffer.add(b"abcde")
    assert headroom_buffer.size == 5
    assert headroom_buffer.position == 3

    assert headroom_buffer.get(5) == b"deabc"
    assert headroom_buffer.size == 0
    assert headroom_buffer.position == 8

    headroom_buffer.add(b"abcde")
    assert headroom_buffer.size == 5
    assert headroom_buffer.position == 8

    assert headroom_buffer.get(5) == b"abcde"
    assert headroom_buffer.size == 0
    assert headroom_buffer.position == 13


def test_enable_disable_protected_after_get_fails(protected):
    # Get something so we are not a position==0
    protected.add(b"abc")
    protected.get(1)

    # This is fine
    protected.protected_headroom = True

    with pytest.raises(InvalidStateError):
        # This is not
        protected.protected_headroom = False


def test_protected_does_not_remove_data(protected):
    # Also test that adding too much data not possible
    protected.add(b"abcdef")
    assert protected.size == 5
    assert protected.position == 0

    assert protected.get(2) == b"ab"
    assert protected.size == 3
    assert protected.position == 2

    assert protected.get(4) == b"cde"
    assert protected.size == 0
    assert protected.position == 5

    assert protected.add(b"ggg") == 0
    assert protected.size == 0
    assert protected.position == 5

    assert protected.seek(0)
    assert protected.size == 5
    assert protected.position == 0

    assert protected.get(5) == b"abcde"
    assert protected.size == 0
    assert protected.position == 5


def test_disable_protected_headroom_after_using_it(protected):
    protected.add(b"abcdef")

    assert protected.get(2) == b"ab"
    assert protected.size == 3
    assert protected.position == 2

    # Seek to beginning to make it possible to disable protected headroom
    assert protected.seek(0)
    protected.protected_headroom = False

    assert protected.get(6) == b"abcde"
    assert protected.size == 0
    assert protected.position == 5

    # Now we can add data again (since not protected)
    assert protected.add(b"hij") == 3
    assert protected.size == 3
    assert protected.position == 5


def test_protected_headroom_constructor():
    buffer = buf.SemiSeekableBuffer(
        BUFFER_SIZE, seekable_headroom=HEADROOM, protected_headroom=True
    )
    buffer.add(b"abcde")

    assert buffer.get(HEADROOM) == b"ab"
    assert buffer.position == 2
    assert buffer.seek(0)
    assert buffer.position == 0


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"a", True),
        (b"aa", True),
        (b"aaa", False),
        (1, True),
        (2, True),
        (3, False),
    ],
)
def test_fits_in_buffer(buffer, data, expected):
    buffer.add(b"abc")
    assert buffer.fits(data) == expected


def test_fits_with_headroom_present(buffer):
    buffer.add(BUFFER_SIZE * b"a")
    buffer.get(1)
    assert not buffer.fits(2)


def test_seek_current_position_ok(buffer):
    assert buffer.seek(0)

    buffer.add(b"a" * BUFFER_SIZE)
    buffer.get(HEADROOM)
    assert not buffer.seek(1)
    assert buffer.seek(2)
