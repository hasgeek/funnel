"""View helpers."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from contextlib import nullcontext
from datetime import datetime, timedelta
from hashlib import blake2b
from os import urandom
from typing import Any, Callable, Dict, Optional, Tuple, Union
from urllib.parse import unquote, urljoin, urlsplit
import gzip
import zlib

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import BuildError, RequestRedirect
from werkzeug.urls import url_quote

from furl import furl
from pytz import common_timezones
from pytz import timezone as pytz_timezone
from pytz import utc
import brotli

from baseframe import cache, statsd
from coaster.sqlalchemy import RoleMixin
from coaster.utils import utcnow

from .. import app, built_assets, shortlinkapp
from ..forms import supported_locales
from ..models import Shortlink, User, db, profanity
from ..proxies import request_wants
from ..typing import ResponseType, ReturnResponse, ReturnView

valid_timezones = set(common_timezones)

nocache_expires = utc.localize(datetime(1990, 1, 1))

# Six avatar colours defined in _variable.scss
avatar_color_count = 6

# --- Classes --------------------------------------------------------------------------


class SessionTimeouts(Dict[str, timedelta]):
    """
    Singleton dictionary that aids tracking timestamps in session.

    Use the :attr:`session_timeouts` instance instead of this class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Create a dictionary that separately tracks {key}_at keys."""
        super().__init__(*args, **kwargs)
        self.keys_at = {f'{key}_at' for key in self.keys()}

    def __setitem__(self, key: str, value: timedelta) -> None:
        """Add or set a value to the dictionary."""
        if key in self:
            raise KeyError(f"Key {key} is already present")
        if not isinstance(value, timedelta):
            raise ValueError("Value must be a timedelta")
        self.keys_at.add(f'{key}_at')
        super().__setitem__(key, value)

    def __delitem__(self, key) -> None:
        """Remove a value from the dictionary."""
        self.keys_at.remove(f'{key}_at')
        super().__delitem__(key)

    def has_intersection(self, other):
        """Check for intersection with other dictionary-like object."""
        okeys = other.keys()
        return not (self.keys_at.isdisjoint(okeys) and self.keys().isdisjoint(okeys))


#: Temporary values that must be periodically expunged from the cookie session
session_timeouts = SessionTimeouts()

# --- Utilities ------------------------------------------------------------------------


def app_context():
    """Return an app context if one is not active."""
    if current_app:
        return nullcontext()
    return app.app_context()


def str_pw_set_at(user: User) -> str:
    """Render user.pw_set_at as a string, for comparison."""
    if user.pw_set_at is not None:
        return user.pw_set_at.astimezone(utc).replace(microsecond=0).isoformat()
    return 'None'


def metarefresh_redirect(url: str):
    """Redirect using a non-standard Refresh header in a Meta tag."""
    return Response(render_template('meta_refresh.html.jinja2', url=url))


def app_url_for(
    target_app: Flask,
    endpoint: str,
    _external: bool = True,
    _method: str = 'GET',
    _anchor: str = None,
    _scheme: str = None,
    **values: str,
) -> str:
    """
    Equivalent of calling `url_for` in another app's context, with some differences.

    - Does not support blueprints as this repo does not use them
    - Does not defer to a :exc:`BuildError` handler. Caller is responsible for handling
    - However, defers to Flask's `url_for` if the provided app is also the current app

    The provided app must have `SERVER_NAME` in its config for URL construction to work.
    """
    if (  # pylint: disable=protected-access
        current_app and current_app._get_current_object() is target_app
    ):
        return url_for(
            endpoint,
            _external=_external,
            _method=_method,
            _anchor=_anchor,
            _scheme=_scheme,
            **values,
        )
    url_adapter = target_app.create_url_adapter(None)
    if url_adapter is None:
        raise BuildError(endpoint, values, _method)
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


def validate_is_app_url(url: Union[str, furl], method: str = 'GET') -> bool:
    """Confirm if an external URL is served by the current app (runtime-only)."""
    # Parse or copy URL and remove username and password before further analysis
    parsed_url = furl(url).remove(username=True, password=True)
    if not parsed_url.host or not parsed_url.scheme:
        return False  # This validator requires a full URL

    if current_app.url_map.host_matching:
        # This URL adapter matches explicit hosts, so we just give it the URL as its
        # server_name
        server_name = parsed_url.netloc
        subdomain = None
    else:
        # Next, validate whether the URL's host/netloc is valid for this app's config
        # or for the hostname indicated by the current request
        subdomain = None

        # If config specifies a SERVER_NAME and app has subdomains, test against it
        server_name = current_app.config['SERVER_NAME']
        if server_name:
            if not (
                parsed_url.netloc == server_name
                or (
                    current_app.subdomain_matching
                    and parsed_url.netloc.endswith(f'.{server_name}')
                )
            ):
                return False
            subdomain = (
                (current_app.url_map.default_subdomain or None)
                if current_app.subdomain_matching
                else None
            )

        # If config does not specify a SERVER_NAME, match against request.host
        if not server_name:
            # Compare request.host with parsed_url.host since there's no port here
            if parsed_url.host != request.host:
                return False
            server_name = request.host

        # Host is validated, now make an adapter to match the path
        adapter = current_app.url_map.bind(
            server_name,
            subdomain=subdomain,
            script_name=current_app.config['APPLICATION_ROOT'],
            url_scheme=current_app.config['PREFERRED_URL_SCHEME'],
        )

    while True:  # Keep looping on redirects
        try:
            return bool(adapter.match(parsed_url.path, method=method))
        except RequestRedirect as exc:
            parsed_url = furl(exc.new_url)
        except (MethodNotAllowed, NotFound):
            return False


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


def get_scheme_netloc(uri: str) -> Tuple[str, str]:
    parsed_uri = urlsplit(uri)
    return (parsed_uri.scheme, parsed_uri.netloc)


def autoset_timezone_and_locale(user: User) -> None:
    # Set the user's timezone and locale automatically if required
    if (
        user.auto_timezone
        or user.timezone is None
        or str(user.timezone) not in valid_timezones
    ):
        if request.cookies.get('timezone'):
            timezone = unquote(request.cookies['timezone'])
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


def progressive_rate_limit_validator(
    token: str, prev_token: Optional[str]
) -> Tuple[bool, bool]:
    """
    Validate for :func:`validate_rate_limit` on autocomplete-type resources.

    Will count progressive keystrokes and backspacing as a single rate limited call, but
    any edits will be counted as a separate call, incrementing the resource usage count.

    :returns: tuple of (bool, bool): (count_this_call, retain_previous_token)
    """
    # prev_token will be None on the first call to the validator. Count the first
    # call, but don't retain the previous token
    if prev_token is None:
        return (True, False)

    # User is typing, so current token is previous token plus extra chars. Don't
    # count this as a new call, and keep the longer current token as the reference
    if token.startswith(prev_token):
        return (False, False)

    # User is backspacing (current < previous), so keep the previous token as the
    # reference in case they retype the deleted characters
    if prev_token.startswith(token):
        return (False, True)

    # Current token is differing from previous token, meaning this is a new query.
    # Increment the counter, discard previous token and use current token as ref
    return (True, False)


def validate_rate_limit(  # pylint: disable=too-many-arguments
    resource: str,
    identifier: str,
    attempts: int,
    timeout: int,
    token: Optional[str] = None,
    validator: Callable[[str, Optional[str]], Tuple[bool, bool]] = None,
):
    """
    Validate a rate limit on API-endpoint resources.

    Confirm the rate limit has not been reached for the given string identifier, number
    of allowed attempts, and timeout period. Uses a simple limiter: once the number of
    attempts is reached, no further attempts can be made for timeout seconds.

    Aborts with HTTP 429 in case the limit has been reached.

    :param str resource: Resource being rate limited
    :param str identifier: Identifier for entity being rate limited
    :param int attempts: Number of attempts allowed
    :param int timeout: Duration in seconds to block after attempts are exhausted
    :param str token: For advanced use, a token to check against for future calls
    :param validator: A validator that receives token and previous token, and returns
        two bools ``(count_this, retain_previous_token)``

    For an example of how the token and validator are used, see
    :func:`progressive_rate_limit_validator` and its users.
    """
    # statsd.set requires an ASCII string. The identifier parameter is typically UGC,
    # meaning it can contain just about any character and any length. The identifier
    # is hashed using BLAKE2b here to bring it down to a meaningful length. It is not
    # reversible should that be needed for debugging, but the obvious alternative Base64
    # encoding (for convering to 7-bit ASCII) cannot be used as it does not limit length
    statsd.set(
        'rate_limit',
        blake2b(identifier.encode(), digest_size=32).hexdigest(),
        rate=1,
        tags={'resource': resource},
    )
    cache_key = f'rate_limit/v1/{resource}/{identifier}'
    # XXX: Typing for cache.get is incorrectly specified as returning Optional[str]
    cache_value: Optional[Tuple[int, str]] = cache.get(  # type: ignore[assignment]
        cache_key
    )
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
    if validator is not None and token is not None:
        do_increment, retain_token = validator(token, cache_token)
        if retain_token:
            token = cache_token
        if do_increment:
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
# 3 bytes will be 4 characters in base64 and will have 2**3 = 16.7m possibilities.
# This number can be increased to 4 as volumes grow, but will result in a 6 char token
TOKEN_BYTES_LEN = 3
# Changing this prefix will break existing tokens. Do not change
TEXT_TOKEN_PREFIX = 'temp_token/v1/'  # nosec  # noqa: S105


def make_cached_token(payload: dict, timeout: int = 24 * 60 * 60) -> str:
    """
    Make a short text token that references data in cache with a timeout period.

    This is currently used for SMS OTPs and links, including for login, password reset
    and SMS unsubscribe. The complementary :func:`retrieve_cached_token` and
    :func:`delete_cached_token` functions can be used to retrieve and discard data.

    This expects (a) the Redis cache to be shared across all HTTP workers, or (b)
    session binding to the worker. Funnel's Docker implementation as introduced in #1292
    isolates Redis cache per worker.

    :param payload: Data to save against the token
    :param timeout: Timeout period for token in seconds (default 24 hours)
    """
    while True:
        token = urlsafe_b64encode(urandom(TOKEN_BYTES_LEN)).decode().rstrip('=')
        if profanity.contains_profanity(token):
            # Contains profanity, try another
            continue
        if cache.get(TEXT_TOKEN_PREFIX + token) is not None:
            # Token in use, try another
            continue
        # All good? Use it
        break

    cache.set(TEXT_TOKEN_PREFIX + token, payload, timeout=timeout)
    return token


def retrieve_cached_token(token: str) -> Optional[dict]:
    """Retrieve cached data given a token generated using :func:`make_cached_token`."""
    # XXX: Typing for cache.get is incorrectly specified as returning Optional[str]
    return cache.get(TEXT_TOKEN_PREFIX + token)  # type: ignore[return-value]


def delete_cached_token(token: str) -> bool:
    """Delete cached data for a token generated using :func:`make_cached_token`."""
    return cache.delete(TEXT_TOKEN_PREFIX + token)


def compress(data: bytes, algorithm: str) -> bytes:
    """
    Compress data using Gzip, Deflate or Brotli.

    :param algorithm: One of ``gzip``, ``deflate`` or ``br``
    """
    if algorithm == 'gzip':
        return gzip.compress(data)
    if algorithm == 'deflate':
        return zlib.compress(data)
    if algorithm == 'br':
        return brotli.compress(data)
    raise ValueError("Unknown compression algorithm")


def decompress(data: bytes, algorithm: str) -> bytes:
    """
    Uncompress data using Gzip, Deflate or Brotli.

    :param algorithm: One of ``gzip``, ``deflate`` or ``br``
    """
    if algorithm == 'gzip':
        return gzip.decompress(data)
    if algorithm == 'deflate':
        return zlib.decompress(data)
    if algorithm == 'br':
        return brotli.decompress(data)
    raise ValueError("Unknown compression algorithm")


def compress_response(response: ResponseType) -> None:
    """
    Conditionally compress a response based on request parameters.

    This function should ideally be used with a cache layer, such as
    :func:`~funnel.views.decorators.etag_cache_for_user`.
    """
    if (  # pylint: disable=too-many-boolean-expressions
        response.content_length is not None
        and response.content_length > 500
        and 200 <= response.status_code < 300
        and 'Content-Encoding' not in response.headers
        and response.mimetype is not None
        and (
            response.mimetype.startswith('text/')
            or response.mimetype
            in (
                'application/json',
                'application/javascript',
            )
        )
    ):
        algorithm = request.accept_encodings.best_match(('br', 'gzip', 'deflate'))
        if algorithm is not None:
            response.set_data(compress(response.get_data(), algorithm))
            response.headers['Content-Encoding'] = algorithm
            response.vary.add('Accept-Encoding')  # type: ignore[union-attr]


# --- Template helpers -----------------------------------------------------------------


def render_redirect(url: str, code: int = 303) -> ReturnResponse:
    """
    Render a redirect that is sensitive to the request type.

    Defaults to 303 redirects to safely handle browser history in POST -> GET
    transitions. Caller must specify 302 for instances where a request is being
    intercepted (typically in a view decorator).
    """
    if request_wants.html_fragment:
        return Response(
            render_template('redirect.html.jinja2', url=url),
            status=200,
            headers={'HX-Redirect': url},
        )
    if request_wants.json:
        response = jsonify({'status': 'error', 'error': 'redirect', 'location': url})
        response.status_code = 422
        response.headers['HX-Redirect'] = url
        return response
    return redirect(url, code)


def html_in_json(template: str) -> Dict[str, Union[str, Callable[[dict], ReturnView]]]:
    """Render a HTML fragment in a JSON wrapper, for use with ``@render_with``."""

    def render_json_with_status(kwargs) -> ReturnResponse:
        """Render plain JSON."""
        return jsonify(
            status='ok',
            **{
                k: v
                if not isinstance(v, RoleMixin)
                else v.current_access(datasets=('primary',))
                for k, v in kwargs.items()
            },
        )

    def render_html_in_json(kwargs) -> ReturnResponse:
        """Render HTML fragment in JSON."""
        resp = jsonify({'status': 'ok', 'html': render_template(template, **kwargs)})
        resp.content_type = 'application/x.html+json; charset=utf-8'
        return resp

    return {
        'text/html': template,
        'application/json': render_json_with_status,
        'application/x.html+json': render_html_in_json,
    }


# --- Filters and URL constructors -----------------------------------------------------


@app.template_filter('url_join')
def url_join(base, url=''):
    """Join URLs in a template filter."""
    return urljoin(base, url)


@app.template_filter('cleanurl')
def cleanurl_filter(url):
    """Clean a URL in a template filter."""
    if not isinstance(url, furl):
        url = furl(url)
    url.path.normalize()
    # Strip leading and trailing slashes in //hostname/path/ to get hostname/path
    return furl().set(netloc=url.netloc, path=url.path).url.strip('/')


@app.template_filter('shortlink')
def shortlink(url: str, actor: Optional[User] = None, shorter: bool = True) -> str:
    """
    Return a short link suitable for sharing, in a template filter.

    Caller must perform a database commit.

    :param shorter: Use a shorter shortlink, ideal for SMS or a small database
    """
    sl = Shortlink.new(url, reuse=True, shorter=shorter, actor=actor)
    db.session.add(sl)
    g.require_db_commit = True
    return app_url_for(shortlinkapp, 'link', name=sl.name, _external=True)


@app.context_processor
def template_context() -> Dict[str, Any]:
    """Add template context items."""
    return {'built_asset': lambda assetname: built_assets[assetname]}


# --- Request/response handlers --------------------------------------------------------


@app.after_request
def commit_db_session(response: ResponseType) -> ResponseType:
    """Commit database session at the end of a request if asked to."""
    # This handler is primarily required for the `|shortlink` template filter, which
    # may make a database entry in a view's ``return render_template(...)`` call and
    # is therefore too late for a commit within the view
    if getattr(g, 'require_db_commit', False):
        db.session.commit()
    return response


@app.after_request
def track_temporary_session_vars(response: ResponseType) -> ResponseType:
    """Add timestamps to timed values in session, and remove expired values."""
    # Process timestamps only if there is at least one match. Most requests will
    # have no match.
    if session_timeouts.has_intersection(session):
        for var, delta in session_timeouts.items():
            var_at = f'{var}_at'
            if var in session:
                if var_at not in session:
                    # Session has var but not timestamp, so add a timestamp
                    session[var_at] = utcnow()
                elif session[var_at] < utcnow() - delta:
                    # Session var has expired, so remove var and timestamp
                    session.pop(var)
                    session.pop(var_at)
            elif var_at in session:
                # Timestamp present without var, so remove it
                session.pop(var_at)

    return response


@app.after_request
def cache_expiry_headers(response: ResponseType) -> ResponseType:
    if response.expires is None:
        response.expires = nocache_expires
    if not response.cache_control.max_age:
        response.cache_control.max_age = 0
    return response
