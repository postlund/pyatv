"""Unit tests for pyatv.support.metadata."""
import pytest

from pyatv.interface import MediaMetadata
from pyatv.support.metadata import merge_into

METADATA_FIELDS = list(MediaMetadata.__dataclass_fields__.keys())


def test_returns_base_instance():
    base = MediaMetadata()
    new_metadata = MediaMetadata()
    merged = merge_into(base, new_metadata)
    assert merged is base


def test_to_empty_metadata():
    # This basically sets the title field to "title", artist to "artist" and so on
    # for all fields and assert that it is correct
    metadata = merge_into(MediaMetadata(), MediaMetadata(*METADATA_FIELDS))
    for field in METADATA_FIELDS:
        assert getattr(metadata, field) == field


def test_no_override_set_value():
    metadata = merge_into(
        MediaMetadata(title="title"), MediaMetadata(title="new title")
    )
    assert metadata.title == "title"
