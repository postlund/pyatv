"""Collections for pyatv."""
import collections.abc
import typing

T = typing.TypeVar("T")


def dict_merge(
    dict_a: typing.Dict[typing.Any, typing.Any],
    dict_b: typing.Mapping[typing.Any, typing.Any],
) -> typing.Dict[typing.Any, typing.Any]:
    """Merge items from dict_b into dict_a, not overriding existing keys.

    This is effectively the same as the merge operator in python 3.9: dict_a | dict_b
    """
    dict_a.update({key: value for key, value in dict_b.items() if key not in dict_a})
    return dict_a


class CaseInsensitiveDict(  # pylint: disable=too-many-ancestors
    typing.MutableMapping[str, T]
):
    """A mapping where the keys are compared case-insensitively.

    As a consequence of this, the keys *must* be strings.
    """

    _data: typing.Dict[str, T]

    @staticmethod
    def _lower_key(key_value: typing.Tuple[str, T]) -> typing.Tuple[str, T]:
        key, value = key_value
        return key.lower(), value

    def __init__(
        self,
        mapping_or_iterable: typing.Union[
            typing.Mapping[str, T], typing.Iterable[typing.Tuple[str, T]], None
        ] = None,
        **kwargs
    ):
        """Create a `CaseInensitiveDict`. It takes the same arguments as `dict`."""
        self._data = {}
        if isinstance(mapping_or_iterable, collections.abc.Mapping):
            self._data.update(map(self._lower_key, mapping_or_iterable.items()))
        elif isinstance(mapping_or_iterable, collections.abc.Iterable):
            self._data.update(
                # It doesn't look like mypy goes deep enough to check this properly, (it
                # thinks the argument to the callable should be a sequence of objects,
                # not an iterable of tuples) so casting it is.
                map(
                    typing.cast(
                        typing.Callable[
                            [typing.Sequence[object]], typing.Tuple[str, T]
                        ],
                        self._lower_key,
                    ),
                    mapping_or_iterable,
                )
            )
        if kwargs:
            self._data.update(map(self._lower_key, kwargs.items()))

    def __getitem__(self, key: str) -> T:
        """Get a value referenced by a string key, compared case-insensitively."""
        return self._data[key.lower()]

    def __setitem__(self, key: str, value: T):
        """Set a value referenced by a string key, compared case-insensitively."""
        self._data[key.lower()] = value

    def __delitem__(self, key: str):
        """Delete a value referenced by a string key, compared case-insensitively."""
        del self._data[key.lower()]

    def __contains__(self, key) -> bool:
        """Check if a key is present in the dictionary, compared case-insensitively."""
        try:
            return super().__contains__(key.lower())
        except AttributeError:
            return NotImplemented

    def __len__(self) -> int:
        """Get the number of keys (and values) present in the mapping."""
        return len(self._data)

    def __iter__(self) -> typing.Iterator[str]:
        """Return an iterator over the mapping keys."""
        return iter(self._data)

    def __eq__(self, other) -> bool:
        """Comparetwo dictionaries, with keys compared case-insensitively."""
        if isinstance(other, CaseInsensitiveDict):
            # If it's another CaseInsensitiveDict, super easy
            return self._data == other._data
        if isinstance(other, collections.abc.Mapping):
            # if it's not, but it is a dict, attempt to lower the keys of the other dict
            for other_key, other_value in other.items():
                try:
                    lowered_key = other_key.lower()
                except AttributeError:
                    # If the other keys aren't strings, these dicts aren't equal
                    return False
                if other_value != self[lowered_key]:
                    return False
            return True
        raise NotImplementedError

    def __str__(self) -> str:
        """Return string representation of instance."""
        return str(self._data)

    def __repr__(self) -> str:
        """Return representation of instance."""
        return repr(self._data)
