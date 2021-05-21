"""Simple FIFO for packets based on dict.

This FIFO holds a certain number of elements as defined by upper_limit. Each item maps a
sequence number to a packet, allowing fast look up of a certain packet. The order is
defined by insertion order and *not* sequence number order.

When upper limit is exceeded, the item that was *inserted* last, is removed.

Example:
fifo = PacketFifo(2)
fifo[1] = 123
fifo[2] = 456
print(fifo[1], fifo[2])
"""

from typing import Dict, Iterator, MutableMapping, TypeVar

T = TypeVar("T")


class PacketFifo(MutableMapping[int, T]):  # pylint: disable=too-many-ancestors
    """Implementation of simple packet FIFO."""

    _items: Dict[int, T]

    def __init__(self, upper_limit: int) -> None:
        """Initialize a new PacketFifo instance."""
        self._items = {}
        self._upper_limit = upper_limit

    def clear(self):
        """Remove all items in FIFO."""
        self._items.clear()

    def __len__(self) -> int:
        """Return number of items in FIFO."""
        return len(self._items)

    def __setitem__(self, index: int, value: T):
        """Add an items to FIFO."""
        if isinstance(index, int):
            # Cannot add item with same index again
            if index in self._items:
                raise ValueError(f"{index} already in FIFO")

            # Remove oldest item if limit is exceeded
            if len(self) + 1 > self._upper_limit:
                del self._items[list(self._items.keys())[0]]

            self._items[index] = value
        else:
            raise TypeError("only int supported as key")

    def __delitem__(self, index: int) -> None:
        """Remove item from FIFO."""
        raise NotImplementedError("removing items not supported")

    def __iter__(self) -> Iterator[int]:
        """Iterate over indices in FIFO."""
        return self._items.__iter__()

    def __getitem__(self, index: int) -> T:
        """Return value of an item."""
        if isinstance(index, int):
            return self._items[index]
        raise TypeError("only int supported as key")

    def __contains__(self, index: object) -> bool:
        """Return if an element exists in FIFO."""
        return index in self._items

    def __str__(self) -> str:
        """Return string representation of FIFO.

        Only index numbers are returned in the string.
        """
        return str(list(self._items.keys()))

    def __repr__(self) -> str:
        """Return internal representation as string of FIFO."""
        return repr(self._items)
