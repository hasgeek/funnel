"""Miscellaneous utility functions."""

from __future__ import annotations

import io
import urllib.parse
from hashlib import blake2b
from typing import overload

import phonenumbers
import qrcode
import qrcode.image.svg
from flask import abort

__all__ = [
    'blake2b160_hex',
    'abort_null',
    'make_redirect_url',
    'mask_email',
    'mask_phone',
    'extract_twitter_handle',
    'format_twitter_handle',
    'split_name',
    'make_qrcode',
]

MASK_DIGITS = str.maketrans('0123456789', '•' * 10)

# --- Utilities ------------------------------------------------------------------------


def blake2b160_hex(text: str) -> str:
    """BLAKE2b hex digest of the given text using digest size 20 (160 bits)."""
    return blake2b(text.encode('utf-8'), digest_size=20).hexdigest()


@overload
def abort_null(text: str) -> str:
    ...


@overload
def abort_null(text: None) -> None:
    ...


def abort_null(text: str | None) -> str | None:
    """
    Abort request if text contains null characters.

    Throws HTTP (400) Bad Request if text is tainted, returns text otherwise.
    """
    if text is not None and '\x00' in text:
        abort(400)
    return text


def make_redirect_url(
    url: str, use_fragment: bool = False, **params: str | int | None
) -> str:
    """
    Make an OAuth2 redirect URL.

    :param bool use_fragments: Insert parameters into the fragment rather than the query
        component of the URL. This is required for OAuth2 public clients
    """
    urlparts = list(urllib.parse.urlsplit(url))
    # URL parts:
    # 0: scheme
    # 1: netloc
    # 2: path
    # 3: query -- appended to
    # 4: fragment
    queryparts = urllib.parse.parse_qsl(
        urlparts[4] if use_fragment else urlparts[3], keep_blank_values=True
    )
    queryparts.extend([(k, str(v)) for k, v in params.items() if v is not None])
    if use_fragment:
        urlparts[4] = urllib.parse.urlencode(queryparts)
    else:
        urlparts[3] = urllib.parse.urlencode(queryparts)
    return urllib.parse.urlunsplit(urlparts)


def mask_email(email: str) -> str:
    """Mask an email address to only offer a hint of what it is."""
    if '@' not in email:
        return f'{email[0]}••••'
    username, domain = email.split('@', 1)
    return f'{username[0]}••••@{domain[0]}••••'


def mask_phone(phone: str) -> str:
    """Mask a valid phone number to only reveal the country code and last two digits."""
    parsed = phonenumbers.parse(phone)
    formatted = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    cc_prefix = f'+{parsed.country_code}'
    if formatted.startswith(cc_prefix):
        prefix, middle, suffix = (
            cc_prefix,
            formatted[len(cc_prefix) : -2],
            formatted[-2:],
        )
    else:
        prefix, middle, suffix = '', formatted[:-2], formatted[-2:]

    middle = middle.translate(MASK_DIGITS)

    return f'{prefix}{middle}{suffix}'


def extract_twitter_handle(handle: str) -> str | None:
    """
    Extract a twitter handle from a user input.

    Usage::

        >>> extract_twitter_handle('https://twitter.com/marscuriosity')
        'marscuriosity'

    **Notes**

    - Returns `None` for invalid cases.
    - Twitter restricts the length of handles to 15. 16 is the threshold here, since a
      user might prefix their handle with an '@', a valid case.
    - Tests in `tests/test_util.py`.
    """
    if not handle:
        return None

    parsed_handle = urllib.parse.urlsplit(handle)
    if (
        (parsed_handle.netloc and parsed_handle.netloc != 'twitter.com')
        or (not parsed_handle.netloc and len(handle) > 16)
        or (not parsed_handle.path)
    ):
        return None

    return str([part for part in parsed_handle.path.split('/') if part][0]).replace(
        '@', ''
    )


def format_twitter_handle(handle: str | None) -> str:
    """Format twitter handle as an @ mention."""
    return f"@{handle}" if handle else ""


def split_name(fullname: str) -> list:
    """
    Split a given fullname into a first name and remaining names.

    Eg: "ABC DEF EFG" -> ["ABC", "DEF EFG"]
        "ABC" -> ["ABC", ""]
    """
    parts = fullname.split(None, 1)
    if len(parts) == 1:
        parts += ['']
    return parts


# TODO: Added tests for this
def make_qrcode(data: str) -> str:
    """Make a QR code in-memory and return the raw SVG."""
    factory = qrcode.image.svg.SvgPathImage
    stream = io.BytesIO()
    img = qrcode.make(data, image_factory=factory)
    img.save(stream)
    qrcode_svg = stream.getvalue()
    stream.close()
    return qrcode_svg.decode('utf-8')
