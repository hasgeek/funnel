import six

import re
import urllib.parse

from flask import current_app

import qrcode
import qrcode.image.svg
import requests

from baseframe import cache

# --- Constants ---------------------------------------------------------------

PHONE_STRIP_RE = re.compile(r'[\t .()\[\]-]+')
PHONE_VALID_RE = re.compile(r'^\+[0-9]+$')

# --- Utilities ---------------------------------------------------------------


def strip_null(text):
    # Removes null byte from given text
    if text is not None:
        return text.replace('\x00', '')


def make_redirect_url(url, use_fragment=False, **params):
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
    queryparts = [
        (
            key.encode('utf-8') if isinstance(key, str) else key,
            value.encode('utf-8') if isinstance(value, str) else value,
        )
        for key, value in queryparts
    ]
    if use_fragment:
        urlparts[4] = urllib.parse.urlencode(queryparts)
    else:
        urlparts[3] = urllib.parse.urlencode(queryparts)
    return urllib.parse.urlunsplit(urlparts)


def strip_phone(candidate):
    return PHONE_STRIP_RE.sub('', candidate)


def valid_phone(candidate):
    return not PHONE_VALID_RE.search(candidate) is None


def mask_email(email):
    """
    Masks an email address

    >>> mask_email(u'foobar@example.com')
    u'f****@e****'
    >>> mask_email(u'not-email')
    u'n****'
    """
    if '@' not in email:
        return '{e}****'.format(e=email[0])
    username, domain = email.split('@')
    return '{u}****@{d}****'.format(u=username[0], d=domain[0])


@cache.memoize(timeout=86400)
def geonameid_from_location(text):
    """
    Convert location string into a set of matching geonameids.

    Eg: "Bangalore" -> {1277333}

    Returns an empty set if the request timed out, or if the Hascore config
    wasn't set.
    To detect multiple locations, split them up and pass each location individually
    """
    if 'HASCORE_SERVER' in current_app.config:
        url = urllib.parse.urljoin(
            current_app.config['HASCORE_SERVER'], '/1/geo/parse_locations'
        )
        try:
            response = requests.get(url, params={'q': text}, timeout=2.0).json()
            geonameids = [
                field['geoname']['geonameid']
                for field in response['result']
                if 'geoname' in field
            ]
            return set(geonameids)
        except requests.exceptions.Timeout:
            pass
    return set()


def extract_twitter_handle(handle):
    """
    Extract a twitter handle from a user input.

    Usage::

        >>> extract_twitter_handle('https://twitter.com/marscuriosity')
        u'marscuriosity'

    **Notes**

    - Returns `None` for invalid cases.
    - Twitter restricts the length of handles to 15. 16 is the threshold here, since a user might prefix their handle with an '@', a valid case.
    - Tests in `tests/test_util.py`.
    """
    if not handle:
        return None

    parsed_handle = urllib.parse.urlparse(handle)
    if (
        (parsed_handle.netloc and parsed_handle.netloc != 'twitter.com')
        or (not parsed_handle.netloc and len(handle) > 16)
        or (not parsed_handle.path)
    ):
        return None

    return str([part for part in parsed_handle.path.split('/') if part][0]).replace(
        '@', ''
    )


def format_twitter_handle(handle):
    return "@{handle}".format(handle=handle) if handle else ""


def split_name(fullname):
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
def make_qrcode(data):
    """Make a QR code in-memory and return the raw svg"""
    factory = qrcode.image.svg.SvgPathImage
    stream = six.BytesIO()
    img = qrcode.make(data, image_factory=factory)
    img.save(stream)
    qrcode_svg = stream.getvalue()
    stream.close()
    return qrcode_svg.decode('utf-8')
