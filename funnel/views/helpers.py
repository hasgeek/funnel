# -*- coding: utf-8 -*-

from pytz import timezone as pytz_timezone, utc
from datetime import datetime
from urlparse import urljoin
from funnel import app, funnelapp


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp) / 1000, from_tz, to_tz)


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


@app.template_filter('url_join')
@funnelapp.template_filter('url_join')
def url_join(base, url=''):
    return urljoin(base, url)
