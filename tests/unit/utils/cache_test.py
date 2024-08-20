"""Tests for cache wrapper."""
# pylint: disable=redefined-outer-name,pointless-statement

import pytest
from cachelib import SimpleCache

from funnel.utils import DictCache


@pytest.fixture
def cache() -> SimpleCache:
    return SimpleCache()


@pytest.fixture
def dict_cache(cache) -> DictCache:
    return DictCache(cache)


def test_cache_interface(cache: SimpleCache, dict_cache: DictCache) -> None:
    """Test dict interface to cachelib cache."""
    assert not cache.has('test-key1')
    assert 'test-key1' not in dict_cache
    cache.set('test-key1', 'value1')
    assert cache.has('test-key1')
    assert 'test-key1' in dict_cache
    assert dict_cache['test-key1'] == 'value1'

    assert not cache.has('test-key2')
    assert 'test-key2' not in dict_cache
    dict_cache['test-key2'] = 'value2'
    assert 'test-key2' in dict_cache
    assert cache.has('test-key2')
    assert dict_cache['test-key2'] == 'value2'

    del dict_cache['test-key2']
    assert 'test_key2' not in dict_cache
    assert not cache.has('test-key2')

    with pytest.raises(KeyError):
        del dict_cache['test-key2']

    with pytest.raises(KeyError):
        dict_cache['test-key2']

    # Cache is not enumerable
    assert len(dict_cache) == 0
    assert not list(dict_cache)
    assert bool(dict_cache) is True
