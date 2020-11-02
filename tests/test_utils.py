from flask import current_app
from werkzeug.exceptions import BadRequest

import pytest

from funnel.utils import (
    abort_null,
    extract_twitter_handle,
    format_twitter_handle,
    geonameid_from_location,
    split_name,
)


def test_extract_twitter_handle():
    expected = 'shreyas_satish'
    assert extract_twitter_handle('https://twitter.com/shreyas_satish') == expected
    assert (
        extract_twitter_handle('https://twitter.com/shreyas_satish/favorites')
        == expected
    )
    assert extract_twitter_handle('@shreyas_satish') == expected
    assert extract_twitter_handle('shreyas_satish') == expected
    assert extract_twitter_handle('seriouslylongstring') is None
    assert extract_twitter_handle('https://facebook.com/shreyas') is None
    assert extract_twitter_handle('') is None


def test_geonameid_from_location(test_client):
    with current_app.test_request_context('/'):
        location = "Bangalore"
        expected_geonameid = 1277333
        assert expected_geonameid in geonameid_from_location(location)


def test_split_name():
    assert split_name("ABC DEF EFG") == ["ABC", "DEF EFG"]


def test_format_twitter_handle():
    assert format_twitter_handle("testusername") == "@testusername"


def test_null_abort_tainted(test_client):
    with current_app.test_request_context('/'):
        with pytest.raises(expected_exception=BadRequest):
            abort_null('\x00')


def test_null_abort_clean(test_client):
    with current_app.test_request_context('/'):
        expected = abort_null('Sample string')
        assert expected == 'Sample string'
