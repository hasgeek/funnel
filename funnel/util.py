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


def format_twitter(handle):
    """
    formats a user given twitter handle
    Eg: https://twitter.com/shreyas_satish -> shreyas_satish, @shreyas_satish -> shreyas_satish
    Returns None if handle is Falsy or contains an URL whose domain is not twitter.com
    """
    # Return None for invalid cases
    if not handle or (urlparse(handle).netloc and urlparse(handle).netloc != 'twitter.com'):
        return None

    return unicode([part for part in urlparse(handle).path.split('/') if part][0]).replace('@', '')
