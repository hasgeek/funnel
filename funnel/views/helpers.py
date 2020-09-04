from base64 import urlsafe_b64encode
from datetime import datetime
from os import urandom
from urllib.parse import unquote, urljoin, urlsplit

from flask import Response, abort, current_app, g, render_template, request, url_for
from werkzeug.urls import url_quote

from furl import furl
from pytz import common_timezones
from pytz import timezone as pytz_timezone
from pytz import utc

from baseframe import cache, statsd

from .. import app, funnelapp, lastuserapp
from ..forms import supported_locales
from ..signals import emailaddress_refcount_dropping
from .jobs import forget_email

valid_timezones = set(common_timezones)


# --- Utilities ------------------------------------------------------------------------


def metarefresh_redirect(url):
    return Response(render_template('meta_refresh.html.jinja2', url=url))


def app_url_for(
    app, endpoint, _external=True, _method='GET', _anchor=None, _scheme=None, **values
):
    """
    Equivalent of calling `url_for` in another app's context, with some differences.

    - Does not support blueprints as this repo does not use them
    - Does not defer to a :exc:`BuildError` handler. Caller is responsible for handling
    - However, defers to Flask's `url_for` if the provided app is also the current app

    The provided app must have `SERVER_NAME` in its config for URL construction to work.
    """
    # 'app' here is the parameter, not the module-level import
    if current_app and current_app._get_current_object() is app:
        return url_for(
            endpoint,
            _external=_external,
            _method=_method,
            _anchor=_anchor,
            _scheme=_scheme,
            **values,
        )
    url_adapter = app.create_url_adapter(None)
    old_scheme = None
    if _scheme is not None:
        old_scheme = url_adapter.url_scheme
        url_adapter.url_scheme = _scheme
    try:
        result = url_adapter.build(
            endpoint, values, method=_method, force_external=_external
        )
    finally:
        if old_scheme is not None:
            url_adapter.url_scheme = old_scheme
    if _anchor:
        result += f'#{url_quote(_anchor)}'
    return result


def mask_email(email):
    """
    Masks an email address to obfuscate it while (hopefully) keeping it recognisable.

    >>> mask_email('foobar@example.com')
    'foo***@example.com'
    >>> mask_email('not-email')
    'not-em***'
    """
    if '@' not in email:
        return '{e}***'.format(e=email[:-3])
    username, domain = email.split('@')
    return '{u}***@{d}'.format(u=username[:-3], d=domain)


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp) / 1000, from_tz, to_tz)


def localize_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(date, from_tz=utc, to_tz=utc):
    if from_tz and to_tz:
        if isinstance(from_tz, str):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, str):
            to_tz = pytz_timezone(to_tz)
        if date.tzinfo is None:
            date = from_tz.localize(date)
        return date.astimezone(to_tz)
    return date


def get_scheme_netloc(uri):
    parsed_uri = urlsplit(uri)
    return (parsed_uri.scheme, parsed_uri.netloc)


def autoset_timezone_and_locale(user):
    # Set the user's timezone and locale automatically if required
    if (
        user.auto_timezone
        or user.timezone is None
        or str(user.timezone) not in valid_timezones
    ):
        if request.cookies.get('timezone'):
            timezone = unquote(request.cookies.get('timezone'))
            if timezone in valid_timezones:
                user.timezone = timezone
    if (
        user.auto_locale
        or user.locale is None
        or str(user.locale) not in supported_locales
    ):
        user.locale = (
            request.accept_languages.best_match(supported_locales.keys()) or 'en'
        )


def validate_rate_limit(
    resource, identifier, attempts, timeout, token=None, validator=None
):
    """
    Confirm the rate limit has not been reached for the given string identifier, number
    of attempts, and timeout period. Uses a simple limiter: once the number of attempts
    is reached, no further attempts can be made for timeout seconds.

    Aborts with HTTP 429 in case the limit has been reached.

    :param str resource: Resource being rate limited
    :param str identifier: Identifier for entity being rate limited
    :param int attempts: Number of attempts allowed
    :param int timeout: Duration in seconds to block after attempts are exhausted
    :param str token: For advanced use, a token to check against for future calls
    :param validator: A validator that receives the token and returns two bools
        ``(count_this, retain_previous_token)``

    For an example of how the token and validator are used, see the user_autocomplete
    endpoint in views/auth_resource.py
    """
    statsd.set('rate_limit', identifier, rate=1, tags={'resource': resource})
    cache_key = 'rate_limit/v1/%s/%s' % (resource, identifier)
    cache_value = cache.get(cache_key)
    if cache_value is None:
        count, cache_token = None, None
        statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 201})
    else:
        count, cache_token = cache_value
    if not count or not isinstance(count, int):
        count = 0
    if count >= attempts:
        statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 429})
        abort(429)
    if validator is not None:
        result, retain_token = validator(cache_token)
        if retain_token:
            token = cache_token
        if result:
            current_app.logger.debug(
                "Rate limit +1 (validated with %s, retain %r) for %s/%s",
                cache_token,
                retain_token,
                resource,
                identifier,
            )
            count += 1
            statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 200})
        else:
            current_app.logger.debug(
                "Rate limit +0 (validated with %s, retain %r) for %s/%s",
                cache_token,
                retain_token,
                resource,
                identifier,
            )
    else:
        current_app.logger.debug("Rate limit +1 for %s/%s", resource, identifier)
        count += 1
        statsd.incr('rate_limit', tags={'resource': resource, 'status_code': 200})
    # Always set count, regardless of validator output
    current_app.logger.debug(
        "Setting rate limit usage for %s/%s to %s with token %s",
        resource,
        identifier,
        count,
        token,
    )
    cache.set(cache_key, (count, token), timeout=timeout)


# Text token length in bytes
# 3 bytes will be 4 characters in base64 and will have 2**3 = 16.7m possibilities
TOKEN_BYTES_LEN = 3
text_token_prefix = 'temp_token/v1/'


def make_cached_token(payload, timeout=24 * 60 * 60, reserved=None):
    """
    Make a short text token that caches data with a timeout period.

    :param dict payload: Data to save against the token
    :param int timeout: Timeout period for token in seconds (default 24 hours)
    :param set reserved: Reserved words that should not be used as token
    """
    while True:
        token = urlsafe_b64encode(urandom(TOKEN_BYTES_LEN)).decode().rstrip('=')
        if reserved and token in reserved:
            continue  # Reserved word, try again

        existing = cache.get(text_token_prefix + token)
        if existing:
            continue  # Token in use, try again

        break

    cache.set(text_token_prefix + token, payload, timeout=timeout)
    return token


def retrieve_cached_token(token):
    return cache.get(text_token_prefix + token)


def delete_cached_token(token):
    return cache.delete(text_token_prefix + token)


# --- Filters and URL constructors -----------------------------------------------------


@app.template_filter('url_join')
@funnelapp.template_filter('url_join')
@lastuserapp.template_filter('url_join')
def url_join(base, url=''):
    return urljoin(base, url)


@app.template_filter('cleanurl')
@funnelapp.template_filter('cleanurl')
@lastuserapp.template_filter('cleanurl')
def cleanurl_filter(url):
    if not isinstance(url, furl):
        url = furl(url)
    url.path.normalize()
    return furl().set(netloc=url.netloc, path=url.path).url.lstrip('//').rstrip('/')


@funnelapp.url_defaults
def add_profile_parameter(endpoint, values):
    if funnelapp.url_map.is_endpoint_expecting(endpoint, 'profile'):
        if 'profile' not in values:
            values['profile'] = g.profile.name if g.profile else None


@app.template_filter('shortlink')
@funnelapp.template_filter('shortlink')
@lastuserapp.template_filter('shortlink')
def shortlink(url):
    """Return a short link suitable for SMS."""
    return url  # TODO


# --- Request/response handlers --------------------------------------------------------


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def cache_expiry_headers(response):
    if 'Expires' not in response.headers:
        response.headers['Expires'] = 'Fri, 01 Jan 1990 00:00:00 GMT'
    if 'Cache-Control' in response.headers:
        if 'private' not in response.headers['Cache-Control']:
            response.headers['Cache-Control'] = (
                'private, ' + response.headers['Cache-Control']
            )
    else:
        response.headers['Cache-Control'] = 'private'
    return response


# If an email address had a reference count drop during the request, make a note of
# its email_hash, and at the end of the request, queue a background job. The job will
# call .refcount() and if it still has zero references, it will be marked as forgotten
# by having the email column set to None.

# It is possible for an email address to have its refcount drop and rise again within
# the request, so it's imperative to wait until the end of the request before attempting
# to forget it. Ideally, this job should wait even longer, for several minutes or even
# up to a day.


@emailaddress_refcount_dropping.connect
def forget_email_in_request_teardown(sender):
    if g:  # Only do this if we have an app context
        if not hasattr(g, 'forget_email_hashes'):
            g.forget_email_hashes = set()
        g.forget_email_hashes.add(sender.email_hash)


@app.after_request
@funnelapp.after_request
@lastuserapp.after_request
def forget_email_in_background_job(response):
    if hasattr(g, 'forget_email_hashes'):
        for email_hash in g.forget_email_hashes:
            forget_email.queue(email_hash)
    return response
