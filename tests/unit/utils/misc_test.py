"""Tests for base utilities."""

from werkzeug.exceptions import BadRequest
import pytest

from funnel import utils


def test_make_redirect_url() -> None:
    """Test OAuth2 redirect URL constructor."""
    # scenario 1: straight forward splitting
    result = utils.make_redirect_url('http://example.com/?foo=bar', foo='baz')
    expected_result = 'http://example.com/?foo=bar&foo=baz'
    assert result == expected_result

    # scenario 2: with use_fragment set as True
    result = utils.make_redirect_url(
        'http://example.com/?foo=bar', use_fragment=True, foo='baz'
    )
    expected_result = 'http://example.com/?foo=bar#foo=baz'
    assert result == expected_result


def test_mask_email() -> None:
    """Test for masking email to offer a hint of what it is, without revealing much."""
    assert utils.mask_email('foobar@example.com') == 'f••••@e••••'
    assert utils.mask_email('not-email') == 'n••••'
    assert utils.mask_email('also@not@email') == 'a••••@n••••'


def test_mask_phone() -> None:
    """Test for masking a phone number to only reveal CC and last two digits."""
    assert utils.mask_phone('+18001234567') == '+1 •••-•••-••67'
    assert utils.mask_phone('+919845012345') == '+91 ••••• •••45'


def test_extract_twitter_handle() -> None:
    """Test for extracing a Twitter handle from a URL or username."""
    expected = 'shreyas_satish'
    assert (
        utils.extract_twitter_handle('https://twitter.com/shreyas_satish') == expected
    )
    assert (
        utils.extract_twitter_handle('https://twitter.com/shreyas_satish/favorites')
        == expected
    )
    assert utils.extract_twitter_handle('@shreyas_satish') == expected
    assert utils.extract_twitter_handle('shreyas_satish') == expected
    assert utils.extract_twitter_handle('seriouslylongstring') is None
    assert utils.extract_twitter_handle('https://facebook.com/shreyas') is None
    assert utils.extract_twitter_handle('') is None


def test_split_name() -> None:
    """Test for splitting a name to extract first name (for name badges)."""
    assert utils.split_name("ABC DEF EFG") == ["ABC", "DEF EFG"]


def test_format_twitter_handle() -> None:
    """Test for formatting a Twitter handle into an @handle."""
    assert utils.format_twitter_handle("testusername") == "@testusername"


def test_abort_null() -> None:
    """Test that abort_null raises an exception if the input has a null byte."""
    assert utils.abort_null('all okay') == 'all okay'
    with pytest.raises(BadRequest):
        utils.abort_null('\x00')
    with pytest.raises(BadRequest):
        utils.abort_null('insert\x00null')
