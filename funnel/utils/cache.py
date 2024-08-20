"""Cache wrapper."""

from collections.abc import Iterator, MutableMapping
from typing import Any

from cachelib import BaseCache
from flask_caching import Cache as CacheExtension

__all__ = ['DictCache']

_marker = object()


class DictCache(MutableMapping):
    """
    Provide a dict-like interface to a Cachelib cache.

    This object has three significant differences from regular dicts:

    1. Since a cache can't be enumerated, this object will behave like an empty dict.
    2. However, this object is always truthy despite appearing to be empty.
    3. `None` is a special value indicating a cache miss and can't be used as a value.

    :param cache: Flask-Caching cache backend to wrap
    :param prefix: Prefix string to apply to all keys
    :param timeout: Timeout when setting a value
    """

    def __init__(
        self,
        cache: CacheExtension | BaseCache,
        prefix: str = '',
        timeout: int | None = None,
    ) -> None:
        self.cache = cache
        self.prefix = prefix
        self.timeout = timeout

    def __getitem__(self, key: str) -> Any:
        result = self.cache.get(self.prefix + key)
        if result is not None:
            return result
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        success = self.cache.set(self.prefix + key, value, timeout=self.timeout)
        if not success:
            raise KeyError(key)

    def __delitem__(self, key: str) -> None:
        success = self.cache.delete(self.prefix + key)
        if not success:
            raise KeyError(key)

    def __contains__(self, key: Any) -> bool:
        return self.cache.has(key)

    # Dummy implementations for compatibility with MutableMapping:

    def __iter__(self) -> Iterator:
        """Return an empty iterable since the cache's contents can't be enumerated."""
        return iter(())

    def __len__(self) -> int:
        """Return 0 since the cache's size is not queryable."""
        return 0

    def __bool__(self) -> bool:
        """Return True since the cache can't be iterated and is assumed non-empty."""
        return True
