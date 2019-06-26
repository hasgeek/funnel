import six
import requests
from urlparse import urljoin
from urlparse import urlparse
from flask import current_app
from baseframe import cache
import qrcode
import qrcode.image.svg


@cache.memoize(timeout=86400)
def geonameid_from_location(text):
    """
    Accepts a string, checks hascore if there's a location embedded
    in the string, and returns a set of matched geonameids.
    Eg: "Bangalore" -> {1277333}

    Returns an empty set if the request timed out, or if the Hascore config
    wasn't set.
    To detect multiple locations, split them up and pass each location individually
    """
    if 'HASCORE_SERVER' in current_app.config:
        url = urljoin(current_app.config['HASCORE_SERVER'], '/1/geo/parse_locations')
        try:
            response = requests.get(url, params={'q': text}, timeout=2.0).json()
            geonameids = [field['geoname']['geonameid'] for field in response['result'] if 'geoname' in field]
            return set(geonameids)
        except requests.exceptions.Timeout:
            pass
    return set()


def extract_twitter_handle(handle):
    """
    Extracts a twitter handle from a user input.

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

    parsed_handle = urlparse(handle)
    if ((parsed_handle.netloc and parsed_handle.netloc != 'twitter.com')
            or (not parsed_handle.netloc and len(handle) > 16)
            or (not parsed_handle.path)):
        return None

    return unicode([part for part in parsed_handle.path.split('/') if part][0]).replace('@', '')


def format_twitter_handle(handle):
    return "@{handle}".format(handle=handle) if handle else ""


def split_name(fullname):
    """
    Splits a given fullname into two parts
    a first name, and a concanetated last name.
    Eg: "ABC DEF EFG" -> ("ABC", "DEF EFG")
    """
    if not fullname:
        return fullname
    name_splits = fullname.split()
    return unicode(name_splits[0]), unicode(" ".join([s for s in name_splits[1:]]))


# TODO: Added tests for this
def make_qrcode(data):
    """
    Makes a QR code in-memory and returns the raw svg
    """
    factory = qrcode.image.svg.SvgPathImage
    stream = six.BytesIO()
    img = qrcode.make(data, image_factory=factory)
    img.save(stream)
    qrcode_svg = stream.getvalue()
    stream.close()
    return qrcode_svg
