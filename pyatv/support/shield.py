"""The shield module helps restricting access to an object.

A shielded object can use the @guard decorator to block calls to particular methods
when block has been called:

```python
from pyatv.support.shield import block, guard, shield
class MyClass:
    @guard
    def guarded(self):
        print("do something")


obj = shield(MyClass())
obj.guarded()
block(obj)
obj.guarded()
```

Running this code would yield something like this:

```raw
do something
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File ".../pyatv/pyatv/support/shield.py", line 70, in _guard_method
    raise BlockedStateError(f"{func.__name__} is blocked")
pyatv.exceptions.BlockedStateError: guarded is blocked
```

"""

from functools import wraps
from typing import TypeVar

from pyatv.exceptions import BlockedStateError, InvalidStateError

_SHIELD_VAR = "__shield_is_blocking"

T = TypeVar("T")


def shield(obj: T) -> T:
    """Add shielding to an object."""
    setattr(obj, _SHIELD_VAR, False)
    return obj


def is_shielded(obj: T) -> bool:
    """Return if an object is shielded."""
    return hasattr(obj, _SHIELD_VAR)


def block(obj: T) -> None:
    """Change a shielded object into blocking state."""
    if not is_shielded(obj):
        raise InvalidStateError("object is not shielded")
    setattr(obj, _SHIELD_VAR, True)


def is_blocking(obj: T) -> bool:
    """Return if a shielded object is in blocking state."""
    return is_shielded(obj) and getattr(obj, _SHIELD_VAR)


def guard(func):
    """Guard a function in a shielded object from being called."""

    @wraps(func)
    def _guard_method(self, *args, **kwargs):
        if is_blocking(self):
            raise BlockedStateError(f"{func.__name__} is blocked")
        return func(self, *args, **kwargs)

    return _guard_method
