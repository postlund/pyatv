"""Compatibility module for pydantic.

This module provides some compatibility methods to support both pydantic v1 and v2 in
pyatv. Ideally only v2 should be supported, but due to Home Assistant being stuck at v1
for now, backwards compatibility will be provided until that is resolved. More info in
https://github.com/postlund/pyatv/issues/2261.

The idea is that the rest of the code never imports anything directly from pydantic,
but instead getting import from here. That makes it easy to remove these changes
later on.
"""

from typing import Any, Mapping

# pylint: disable=unused-import

try:
    from pydantic.v1 import BaseModel, Field, ValidationError  # noqa
    from pydantic.v1 import validator as field_validator  # noqa
except ImportError:
    from pydantic import BaseModel, Field, ValidationError  # noqa
    from pydantic import validator as field_validator  # noqa

# pylint: enable=unused-import


def model_copy(model: BaseModel, /, update: Mapping[str, Any]) -> BaseModel:
    """Model copy compatible with pydantic v2.

    Seems like pydantic v1 carries over keys with None values even though target model
    doesn't have the key. Not the case with v2. This method removes keys with None
    values.
    """
    return model.copy(
        update={key: value for key, value in update.items() if value is not None}
    )
