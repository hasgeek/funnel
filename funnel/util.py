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


def format_twitter(twitter_id):
    """
    formats a user given twitter handle
    Eg: https://twitter.com/shreyas_satish -> shreyas_satish, @shreyas_satish -> shreyas_satish
    """
    return urlparse(str(twitter_id)).path.replace('/', '').replace('@', '')
