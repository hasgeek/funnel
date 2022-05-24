from __future__ import annotations

from hashlib import blake2b
from typing import List, Optional, overload
import io
import urllib.parse

from flask import abort

import qrcode
import qrcode.image.svg

# --- Utilities ------------------------------------------------------------------------


def blake2b160_hex(text: str) -> str:
    """BLAKE2b hash of the given text using digest size 20 (160 bits)."""
    return blake2b(text.encode('utf-8'), digest_size=20).hexdigest()


@overload
def abort_null(text: str) -> str:
    ...


@overload
def abort_null(text: None) -> None:
    ...


def abort_null(text: Optional[str]) -> Optional[str]:
    """
    Abort request if text contains null characters.

    Throws HTTP (400) Bad Request if text is tainted, returns text otherwise.
    """
    if text is not None and '\x00' in text:
        abort(400)
    return text


def make_redirect_url(
    url: str, use_fragment: bool = False, **params: Optional[str]
) -> str:
    """
    Make a redirect URL.

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
    queryparts.extend([(k, v) for k, v in params.items() if v is not None])
    if use_fragment:
        urlparts[4] = urllib.parse.urlencode(queryparts)
    else:
        urlparts[3] = urllib.parse.urlencode(queryparts)
    return urllib.parse.urlunsplit(urlparts)


def mask_email(email: str) -> str:
    """
    Mask an email address.

    >>> mask_email('foobar@example.com')
    'f****@e****'
    >>> mask_email('not-email')
    'n****'
    """
    if '@' not in email:
        return f'{email[0]}****'
    username, domain = email.split('@')
    return f'{username[0]}****@{domain[0]}****'


def extract_twitter_handle(handle: str) -> Optional[str]:
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


def format_twitter_handle(handle: str) -> str:
    return f"@{handle}" if handle else ""


def split_name(fullname: str) -> List:
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
