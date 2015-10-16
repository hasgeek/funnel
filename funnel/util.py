from . import app
import requests
from urlparse import urljoin
from urlparse import urlparse
from baseframe import cache


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
    Eg: https://twitter.com/shreyas_satish -> shreyas_satish, @shreyas_satish -> shreyas_satish
    Returns None for invalid cases.
    """
    # Twitter restricts the length of handles to 15. 16 is the threshold here, since
    # a user might prefix their handle with an '@', a valid case.
    if (
            not handle or
            (urlparse(handle).netloc and urlparse(handle).netloc != 'twitter.com') or
            (not urlparse(handle).netloc and len(handle) > 16)
    ):
        return None

    return unicode([part for part in urlparse(handle).path.split('/') if part][0]).replace('@', '')
