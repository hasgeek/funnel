# -*- coding: utf-8 -*-

from flask import request, abort
from functools import wraps
from urlparse import urlparse
from funnel import app
from pytz import timezone as pytz_timezone, utc
from datetime import datetime


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

def basepath(url):
    """
    Returns the base path of a given a URL
    Eg::

        basepath("https://hasgeek.com/1")
        >> u"https://hasgeek.com

    :param url: A valid URL unicode string. Eg: https://hasgeek.com
    """
    parsed_url = urlparse(url)
    if not (parsed_url.scheme or parsed_url.netloc):
        raise ValueError("Invalid URL")
    return u"{scheme}://{netloc}".format(scheme=parsed_url.scheme, netloc=parsed_url.netloc)

def cors(any_get=False):
    """
    Adds CORS headers to the decorated view function.

    Requires `app.config['ALLOWED_ORIGINS']` to be defined with a list
    of permitted domains. Eg: app.config['ALLOWED_ORIGINS'] = ['https://example.com']

    :param any_get: Specify * on the Access-Control-Allow-Origin for any GET request
    """
    def inner(f):
        def add_headers(resp, origin):
            resp.headers['Access-Control-Allow-Origin'] = origin
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
            # echo the request's headers
            resp.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers')
            # debugging only
            if app.debug:
                resp.headers['Access-Control-Max-Age'] = '1'
            return resp

        @wraps(f)
        def wrapper(*args, **kwargs):
            origin = request.headers.get('Origin')
            if not origin:
                # Firefox doesn't send the Origin header, so read the Referer header instead
                # TODO: Remove this conditional when Firefox starts adding an Origin header
                referer = request.referrer
                if referer:
                    origin = basepath(referer)

                if request.method == 'GET' and any_get:
                    origin = '*'

            if request.method == 'POST' and (not origin or origin not in app.config['ALLOWED_ORIGINS']):
                abort(401)

            if request.method == 'OPTIONS':
                # pre-flight request, check CORS headers directly
                resp = app.make_default_options_response()
            else:
                resp = f(*args, **kwargs)
            return add_headers(resp, origin)

        return wrapper
    return inner
