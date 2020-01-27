"""Simple LRU cache for data based on an identifier."""

from collections import OrderedDict


class Cache:
    """Implementation of simple LRU cache."""

    def __init__(self, limit=16):
        """Initialize a new Cache instance."""
        self.limit = limit
        self.data = OrderedDict()

    def empty(self):
        """Return if cache is empty or not."""
        return not self.data

    def put(self, identifier, data):
        """Put something in the cache."""
        try:
            self.data.pop(identifier)
        except KeyError:
            if len(self.data) >= self.limit:
                self.data.popitem(last=False)
        finally:
            self.data[identifier] = data

    def get(self, identifier):
        """Get something from the cache."""
        value = self.data.pop(identifier)
        self.data[identifier] = value
        return value

    def latest(self):
        """Return identifier of last recently used identifier."""
        if self.empty():
            return None
        return list(self.data.keys())[-1]

    def __contains__(self, identifier):
        """Check if something is in the cache."""
        return identifier in self.data

    def __len__(self):
        """Return number of elements in cache."""
        return len(self.data)
