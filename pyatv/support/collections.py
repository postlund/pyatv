"""Collections for pyatv."""
import typing


class CaseInsensitiveDict(dict):
    """A `dict` where the keys are compared case-insensitively.

    As a consequence of this, the keys *must* be strings.
    """

    def __getitem__(self, key: str) -> typing.Any:
        """Get a value referenced by a string key, compared case-insensitively."""
        return super().__getitem__(key.lower())

    def __setitem__(self, key: str, value: typing.Any):
        """Set a value referenced by a string key, compared case-insensitively."""
        return super().__setitem__(key.lower(), value)

    def __delitem__(self, key: str):
        """Delete a value referenced by a string key, compared case-insensitively."""
        return super().__delitem__(key.lower())

    def __contains__(self, key) -> bool:
        """Check if a key is present in the dictionary, compared case-insensitively."""
        try:
            return super().__contains__(key.lower())
        except AttributeError:
            return NotImplemented

    def __eq__(self, other):
        """Comparetwo dictionaries, with keys compared case-insensitively."""
        if isinstance(other, CaseInsensitiveDict):
            # If it's another CaseInsensitiveDict, super easy
            return super().__eq__(other)
        elif isinstance(other, dict):
            # if it's not, but it is a dict, attempt to lower the keys of the other dict
            try:
                lowered_other = {k.lower(): v for k, v in other.items()}
            except AttributeError:
                # If the other leys aren't strings, these dicts aren't equal
                return False
            return super().__eq__(lowered_other)
        else:
            return NotImplemented

    def get(self, key: str, default: typing.Optional[typing.Any] = None) -> typing.Any:
        """Get a value referenced by a string key, compared case-insensitively."""
        return super().get(key.lower(), default)
