from werkzeug.exceptions import BadRequest

import pytest

from funnel.utils import (
    abort_null,
    extract_twitter_handle,
    format_twitter_handle,
    make_redirect_url,
    mask_email,
    split_name,
)


def test_make_redirect_url():
    # scenario 1: straight forward splitting
    result = make_redirect_url('http://example.com/?foo=bar', foo='baz')
    expected_result = 'http://example.com/?foo=bar&foo=baz'
    assert result == expected_result

    # scenario 2: with use_fragment set as True
    result = make_redirect_url(
        'http://example.com/?foo=bar', use_fragment=True, foo='baz'
    )
    expected_result = 'http://example.com/?foo=bar#foo=baz'
    assert result == expected_result


def test_mask_email():
    assert mask_email('foobar@example.com') == 'f****@e****'


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


def test_split_name():
    assert split_name("ABC DEF EFG") == ["ABC", "DEF EFG"]


def test_format_twitter_handle():
    assert format_twitter_handle("testusername") == "@testusername"


def test_null_abort_tainted():
    with pytest.raises(expected_exception=BadRequest):
        abort_null('\x00')


def test_null_abort_clean():
    expected = abort_null('Sample string')
    assert expected == 'Sample string'
