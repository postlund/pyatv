"""Unit tests for remote artwork URL helpers in MRP."""

from pyatv.protocols.mrp import _ITUNES_ARTWORK_PATH, _remote_artwork_size


def test_remote_artwork_size():
    assert _remote_artwork_size(512, -1) == (512, 512)
    assert _remote_artwork_size(0, -1) == (600, 600)
    assert _remote_artwork_size(0, 300) == (300, 300)
    assert _remote_artwork_size(123, 456) == (123, 456)


def test_itunes_artwork_path():
    assert _ITUNES_ARTWORK_PATH.match(
        "Music115/v4/37/2d/6e/372d6e16-7a32-91f0-1a03-0f2d9dbe389e/093624942788.jpg"
    )
    assert not _ITUNES_ARTWORK_PATH.match("a376675b86624f6d")
    assert not _ITUNES_ARTWORK_PATH.match(
        "https://is1-ssl.mzstatic.com/image/thumb/a.jpg/{w}x{h}bb.{f}"
    )
