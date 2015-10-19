from . import app
import requests
from urlparse import urljoin
from urlparse import urlparse
from baseframe import cache
import qrcode
import qrcode.image.svg


@cache.memoize(timeout=86400)
def geonameid_from_location(text):
    """ Accepts a string, checks hascore if there's a location embedded
        in the string, and returns a set of matched geonameids.
        Eg: "Bangalore" -> {1277333}
        To detect multiple locations, split them up and pass each location individually
    """
    if 'HASCORE_SERVER' in app.config:
        url = urljoin(app.config['HASCORE_SERVER'], '/1/geo/parse_locations')
        response = requests.get(url, params={'q': text}).json()
        geonameids = [field['geoname']['geonameid'] for field in response['result'] if 'geoname' in field]
        return set(geonameids)
    return None


def format_twitter_handle(handle):
    """
    formats a user given twitter handle
    Eg:  -> shreyas_satish, @shreyas_satish -> shreyas_satish
    Returns None for invalid cases.
    Twitter restricts the length of handles to 15. 16 is the threshold here, since
    a user might prefix their handle with an '@', a valid case.
    Tested in tests/test_util.py
    """
    if not handle:
        return None

    parsed_handle = urlparse(handle)
    if (
            (parsed_handle.netloc and parsed_handle.netloc != 'twitter.com') or
            (not parsed_handle.netloc and len(handle) > 16)
    ):
        return None

    return unicode([part for part in parsed_handle.path.split('/') if part][0]).replace('@', '')


def split_name(fullname):
    """
    Splits a given fullname into two parts
    a first name, and a concanetated last name.
    Eg: "ABC DEF EFG" -> ("ABC", "DEF EFG")
    """
    name_splits = fullname.split()
    return name_splits[0], " ".join([s for s in name_splits[1:]])


def file_contents(path):
    """Returns contents of a given file path"""
    file = open(path)
    content = file.read()
    file.close()
    return content


def make_qrcode(data, path):
    """
    Makes a QR code with a given path and returns the raw svg
    Data Format is id:key. Eg: 1:xxxxxxxx
    """
    try:
        qrcode_svg = file_contents(path)
    except:
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(data, image_factory=factory)
        img.save(path)
        qrcode_svg = file_contents(path)
    return qrcode_svg
