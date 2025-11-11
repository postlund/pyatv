"""Compatibility module for pydantic.

This module provides some compatibility methods to support both pydantic v1 and v2 in
pyatv. Ideally only v2 should be supported, but due to Home Assistant being stuck at v1
for now, backwards compatibility will be provided until that is resolved. More info in
https://github.com/postlund/pyatv/issues/2261.

The idea is that the rest of the code never imports anything directly from pydantic,
but instead getting import from here. That makes it easy to remove these changes
later on.
"""

from typing import Any, Mapping, TypeVar

from pydantic import BaseModel

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def model_copy(model: _ModelT, /, update: Mapping[str, Any]) -> _ModelT:
    """Model copy compatible with pydantic v2.

    Seems like pydantic v1 carries over keys with None values even though target model
    doesn't have the key. Not the case with v2. This method removes keys with None
    values.
    """
    return model.model_copy(
        update={key: value for key, value in update.items() if value is not None}
    )
