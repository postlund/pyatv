"""Support for working with NSKeyedArchiver serialized data."""

import plistlib
from typing import Any, List, Optional, Tuple


def read_archive_properties(archive, *paths: List[str]) -> Tuple[Optional[Any], ...]:
    """Get properties from NSKeyedArchiver encoded PList.

    In the absence of a robust NSKeyedArchiver implementation, read one or
    more properties from the archived plist by following UID references.
    """
    data = plistlib.loads(archive)
    results = []

    objects = data["$objects"]
    for path in paths:
        element = data["$top"]
        try:
            for key in path:
                element = element[key]
                if isinstance(element, plistlib.UID):
                    element = objects[element]
            results.append(element)
        except (IndexError, KeyError):
            results.append(None)

    return tuple(results)
