# -*- coding: utf-8 -*-

from pytz import timezone as pytz_timezone, utc
from datetime import datetime
from .. import app
import requests
from urlparse import urljoin


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp)/1000, from_tz, to_tz)


def localize_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(date, from_tz=utc, to_tz=utc):
    if from_tz and to_tz:
        if isinstance(from_tz, basestring):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, basestring):
            to_tz = pytz_timezone(to_tz)
        return from_tz.localize(date).astimezone(to_tz).replace(tzinfo=None)
    return date


def location_geodata(location):
    """ Same as from hasjob/views/helper.py
        TODO: Extract into a common lib.
    """
    if 'HASCORE_SERVER' in app.config:
        if isinstance(location, (list, tuple)):
            url = urljoin(app.config['HASCORE_SERVER'], '/1/geo/get_by_names')
        else:
            url = urljoin(app.config['HASCORE_SERVER'], '/1/geo/get_by_name')
        response = requests.get(url, params={'name': location}).json()
        if response.get('status') == 'ok':
            result = response.get('result', {})
            if isinstance(result, (list, tuple)):
                result = {r['geonameid']: r for r in result}
            return result
    return {}


def parsed_location_geodata(data):
    if 'HASCORE_SERVER' in app.config:
        url = urljoin(app.config['HASCORE_SERVER'], '/1/geo/parse_locations')
        response = requests.get(url, params={'q': data}).json()
        return [field['geoname'] for field in response['result'] if 'geoname' in field.keys()][0]
    return {}


def format_location(location):
    return str(location).strip().lower()


@app.template_filter('is_outstation_speaker')
def is_outstation_speaker(speaker_location_name, speaker_locations, space_location):
    if not speaker_locations or not speaker_locations.get(format_location(speaker_location_name), None):
        return None
    return speaker_locations.get(format_location(speaker_location_name)).get('geonameid') != space_location.get('geonameid')
