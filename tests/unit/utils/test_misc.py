"""Tests for base utilities."""

from werkzeug.exceptions import BadRequest

import pytest

from funnel.utils import (
    abort_null,
    extract_twitter_handle,
    format_twitter_handle,
    make_redirect_url,
    mask_email,
    mask_phone,
    normalize_phone_number,
    split_name,
)


def test_make_redirect_url() -> None:
    """Test OAuth2 redirect URL constructor."""
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


def test_mask_email() -> None:
    """Test for masking email to offer a hint of what it is, without revealing much."""
    assert mask_email('foobar@example.com') == 'f••••@e••••'
    assert mask_email('not-email') == 'n••••'
    assert mask_email('also@not@email') == 'a••••@n••••'


def test_mask_phone() -> None:
    """Test for masking a phone number to only reveal CC and last two digits."""
    assert mask_phone('+18001234567') == '+1 •••-•••-••67'
    assert mask_phone('+919845012345') == '+91 ••••• •••45'


def test_extract_twitter_handle() -> None:
    """Test for extracing a Twitter handle from a URL or username."""
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


def test_split_name() -> None:
    """Test for splitting a name to extract first name (for name badges)."""
    assert split_name("ABC DEF EFG") == ["ABC", "DEF EFG"]


def test_format_twitter_handle() -> None:
    """Test for formatting a Twitter handle into an @handle."""
    assert format_twitter_handle("testusername") == "@testusername"


def test_abort_null() -> None:
    """Test that abort_null raises an exception if the input has a null byte."""
    assert abort_null('all okay') == 'all okay'
    with pytest.raises(BadRequest):
        abort_null('\x00')
    with pytest.raises(BadRequest):
        abort_null('insert\x00null')


@pytest.mark.parametrize(
    ('candidate', 'sms', 'expected'),
    [
        ('9845012345', True, '+919845012345'),
        ('98450-12345', True, '+919845012345'),
        ('+91 98450 12345', True, '+919845012345'),
        ('8022223333', False, '+918022223333'),
        ('junk', False, None),
    ],
)
def test_normalize_phone_number(candidate, expected, sms) -> None:
    """Test that normalize_phone_number is able to parse a number."""
    assert normalize_phone_number(candidate, sms) == expected
