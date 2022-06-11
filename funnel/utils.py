from __future__ import annotations

from hashlib import blake2b
from typing import List, Optional, Union, overload
import io
import urllib.parse

from flask import abort

from typing_extensions import Literal
import phonenumbers
import qrcode
import qrcode.image.svg

# Unprefixed phone numbers are assumed to be a local number in India (+91) or US (+1).
# Both IN and US numbers are 10 digits before prefixes. We try IN first as it's the
# higher priority home region.
PHONE_LOOKUP_REGIONS = ['IN', 'US']

# --- Utilities ------------------------------------------------------------------------


@overload
def normalize_phone_number(candidate: str, sms: Literal[False]) -> Optional[str]:
    ...


@overload
def normalize_phone_number(
    candidate: str, sms: Literal[True]
) -> Optional[Union[str, Literal[False]]]:
    ...


def normalize_phone_number(
    candidate: str, sms: bool = False
) -> Optional[Union[str, Literal[False]]]:
    """
    Attempt to parse a phone number from a candidate and return in E164 format.

    :param sms: Validate that the number is from a range that supports SMS delivery,
        returning `False` if it isn't
    """
    # Assume unprefixed numbers to be a local number in one of the supported common
    # regions. We start with the higher priority home region and return the _first_
    # candidate that is likely to be a valid number. This behaviour differentiates it
    # from similar code in :func:`~funnel.models.utils.getuser`, where the loop exits
    # with the _last_ valid candidate (as it's coupled with a
    # :class:`~funnel.models.user.UserPhone` lookup)
    sms_invalid = False
    try:
        for region in PHONE_LOOKUP_REGIONS:
            parsed_number = phonenumbers.parse(candidate, region)
            if phonenumbers.is_valid_number(parsed_number):
                if sms:
                    if phonenumbers.number_type(parsed_number) not in (
                        phonenumbers.PhoneNumberType.MOBILE,
                        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
                    ):
                        sms_invalid = True
                        continue  # Not valid for SMS
                return phonenumbers.format_number(
                    parsed_number, phonenumbers.PhoneNumberFormat.E164
                )
    except phonenumbers.NumberParseException:
        pass
    # We found a number that is valid, but the caller wanted it to be valid for SMS and
    # it isn't, so return a special flag
    if sms_invalid:
        return False
    return None


def blake2b160_hex(text: str) -> str:
    """BLAKE2b hex digest of the given text using digest size 20 (160 bits)."""
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
