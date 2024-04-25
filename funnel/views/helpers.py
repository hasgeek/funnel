"""View helpers."""

from __future__ import annotations

import gzip
import zlib
import zoneinfo
from base64 import urlsafe_b64encode
from collections.abc import Callable, Iterator, Mapping
from contextlib import nullcontext
from datetime import datetime, timedelta
from hashlib import blake2b
from importlib import resources
from os import urandom
from typing import Any, ContextManager, Literal, Protocol
from urllib.parse import quote, unquote, urljoin

import brotli
from babel import Locale
from flask import (
    Flask,
    Request,
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
from flask.sessions import SessionMixin
from furl import furl
from pytz import BaseTzInfo, timezone as pytz_timezone, utc
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import BuildError, RequestRedirect
from werkzeug.wrappers import Response as BaseResponse

from baseframe import cache, statsd
from coaster.assets import WebpackManifest
from coaster.sqlalchemy import RoleAccessProxy, RoleMixin
from coaster.utils import utcnow
from coaster.views import ClassView

from .. import app, shortlinkapp
from ..auth import CurrentAuth, current_auth
from ..forms import supported_locales
from ..models import Account, Project, Shortlink, db, profanity
from ..proxies import RequestWants, request_wants
from ..typing import ResponseType, ReturnResponse, ReturnView
from ..utils import JinjaTemplateBase, jinja_global, jinja_undefined

nocache_expires = utc.localize(datetime(1990, 1, 1))

# Six avatar colours defined in _variable.scss
avatar_color_count = 6

# MARK: Timezone data ------------------------------------------------------------------

# Get all known timezones from zoneinfo and make a lowercased lookup table
valid_timezones = {_tz.lower(): _tz for _tz in zoneinfo.available_timezones()}
# Get timezone aliases from tzinfo.zi and place them in the lookup table
with (resources.files('tzdata.zoneinfo') / 'tzdata.zi').open(
    'r', encoding='utf-8', errors='strict'
) as _tzdata:
    for _tzline in _tzdata.readlines():
        if _tzline.startswith('L'):
            _tzlink, _tznew, _tzold = _tzline.strip().split()
            valid_timezones[_tzold.lower()] = _tznew

# MARK: Classes ------------------------------------------------------------------------


class AppContextProtocol(Protocol):
    """Read-only protocol for ``flask.g`` within Jinja2 templates."""

    def __getattr__(self, name: str) -> Any: ...
    def get(self, name: str, default: Any | None = None) -> Any: ...
    def __contains__(self, item: str) -> bool: ...
    def __iter__(self) -> Iterator[str]: ...


class JinjaTemplate(JinjaTemplateBase, template=None):
    """Jinja template dataclass base class with type hints for Jinja globals."""

    # Globals provided by Jinja2
    range: Callable = jinja_global()  # noqa: A003
    dict: Callable = jinja_global()  # noqa: A003
    lipsum: Callable = jinja_global()
    cycler: Callable = jinja_global()
    joiner: Callable = jinja_global()
    namespace: Callable = jinja_global()

    # Globals provided by Jinja2 i18n extension
    _: Callable = jinja_global()
    gettext: Callable = jinja_global()
    ngettext: Callable = jinja_global()
    pgettext: Callable = jinja_global()
    npgettext: Callable = jinja_global()

    # Globals provided by Flask when an app context is present
    url_for: Callable[..., str] = jinja_global()  # Get URL for route
    get_flashed_messages: Callable = jinja_global()  # Flash messages
    config: Mapping = jinja_global()  # App config as a read-only dict
    g: AppContextProtocol = jinja_global()  # App context data

    # Globals provided by Flask when a request context is present (not typed `| None`
    # here as only email templates are rendered outside a request)
    request: Request = jinja_global()  # HTTP request data
    session: SessionMixin = jinja_global()  # Cookie session

    # Globals provided by Coaster, Baseframe and Funnel
    current_auth: CurrentAuth = jinja_global()  # Auth data
    current_view: ClassView = jinja_global()  # Current ClassView or ModelView
    manifest: WebpackManifest = jinja_global()  # Webpack manifest loader
    request_is_xhr: Callable[[], bool] = jinja_global()  # Legacy XHR test
    get_locale: Callable[[], Locale] = jinja_global()  # User locale
    csrf_token: Callable[[], str | bytes] = jinja_global()  # CSRF token
    request_wants: RequestWants = jinja_global()  # Request flags


class LayoutTemplate(JinjaTemplate, template='layout.html.jinja2'):
    """Jinja templates that extend ``layout.html.jinja2``."""

    search_query: str = jinja_undefined(default=None)


class FormLayoutTemplate(LayoutTemplate, template='formlayout.html.jinja2'):
    """Jinja templates that extend ``formlayout.html.jinja2``."""

    autosave: bool = jinja_undefined(default=None)
    ref_id: str = jinja_undefined(default=None)


class ProjectLayout(LayoutTemplate, template='project_layout.html.jinja2'):
    """Jinja templates that extend ``project_layout.html.jinja2``."""

    project: Project | RoleAccessProxy[Project]


class ProfileLayout(LayoutTemplate, template='profile_layout.html.jinja2'):
    """Jinja templates that extend ``profile_layout.html.jinja2``."""

    # TODO


class SessionTimeouts(dict[str, timedelta]):
    """
    Singleton dictionary that aids tracking timestamps in session.

    Use the :attr:`session_timeouts` instance instead of this class.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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

    def __delitem__(self, key: str) -> None:
        """Remove a value from the dictionary."""
        self.keys_at.remove(f'{key}_at')
        super().__delitem__(key)

    def has_overlap_with(self, other: Mapping) -> bool:
        """Check for intersection with other dictionary-like object."""
        okeys = other.keys()
        return not (self.keys_at.isdisjoint(okeys) and self.keys().isdisjoint(okeys))

    def crosscheck_session(self, response: ResponseType) -> ResponseType:
        """Add timestamps to timed values in session, and remove expired values."""
        # Process timestamps only if there is at least one match. Most requests will
        # have no match.
        if self.has_overlap_with(session):
            now = utcnow()
            for var, delta in self.items():
                var_at = f'{var}_at'
                if var in session:
                    if var_at not in session:
                        # Session has var but not timestamp, so add a timestamp
                        session[var_at] = now
                    elif session[var_at] < now - delta:
                        # Session var has expired, so remove var and timestamp
                        session.pop(var)
                        session.pop(var_at)
                elif var_at in session:
                    # Timestamp present without var, so remove it
                    session.pop(var_at)
        return response


#: Temporary values that must be periodically expunged from the cookie session
session_timeouts = SessionTimeouts()
app.after_request(session_timeouts.crosscheck_session)

# MARK: Utilities ----------------------------------------------------------------------


def app_context() -> ContextManager:
    """Return an app context if one is not active."""
    if current_app:
        return nullcontext()
    return app.app_context()


def str_pw_set_at(user: Account) -> str:
    """Render user.pw_set_at as a string, for comparison."""
    if user.pw_set_at is not None:
        return user.pw_set_at.astimezone(utc).replace(microsecond=0).isoformat()
    return 'None'


def metarefresh_redirect(url: str) -> Response:
    """Redirect using a non-standard Refresh header in a Meta tag."""
    return Response(render_template('meta_refresh.html.jinja2', url=url))


def app_url_for(
    target_app: Flask,
    endpoint: str,
    _external: bool = True,
    _method: str = 'GET',
    _anchor: str | None = None,
    _scheme: str | None = None,
    **values: str,
) -> str:
    """
    Equivalent of calling `url_for` in another app's context, with some differences.

    - Does not support blueprints as this repo does not use them
    - Does not defer to a :exc:`BuildError` handler. Caller is responsible for handling
    - However, defers to Flask's `url_for` if the provided app is also the current app

    The provided app must have `SERVER_NAME` in its config for URL construction to work.
    """
    # pylint: disable=protected-access
    if (
        current_app
        and current_app._get_current_object()  # type: ignore[attr-defined]
        is target_app
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
        result += f'#{quote(_anchor)}'
    return result


def validate_is_app_url(url: str | furl, method: str = 'GET') -> bool:
    """Confirm if an external URL is served by the current app (runtime-only)."""
    # Parse or copy URL and remove username and password before further analysis
    if isinstance(url, str):
        url = furl(url)
    parsed_url = url.remove(username=True, password=True)
    if not parsed_url.host or not parsed_url.scheme:
        return False  # This validator requires a full URL

    if current_app.url_map.host_matching:
        # This URL adapter matches explicit hosts, so we just give it the URL as its
        # server_name
        server_name = parsed_url.netloc or ''  # Fallback blank str for type checking
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
                    and parsed_url.netloc is not None
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
            return bool(adapter.match(str(parsed_url.path), method=method))
        except RequestRedirect as exc:
            parsed_url = furl(exc.new_url)
        except (MethodNotAllowed, NotFound):
            return False


def localize_micro_timestamp(
    timestamp: float, from_tz: BaseTzInfo | str = utc, to_tz: BaseTzInfo | str = utc
) -> datetime:
    return localize_timestamp(int(timestamp) / 1000, from_tz, to_tz)


def localize_timestamp(
    timestamp: float, from_tz: BaseTzInfo | str = utc, to_tz: BaseTzInfo | str = utc
) -> datetime:
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(
    date: datetime, from_tz: BaseTzInfo | str = utc, to_tz: BaseTzInfo | str = utc
) -> datetime:
    if from_tz and to_tz:
        if isinstance(from_tz, str):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, str):
            to_tz = pytz_timezone(to_tz)
        if date.tzinfo is None:
            date = from_tz.localize(date)
        return date.astimezone(to_tz)
    return date


def get_scheme_netloc(uri: str | furl) -> tuple[str | None, str | None]:
    if isinstance(uri, str):
        uri = furl(uri)
    return uri.scheme, uri.netloc


def autoset_timezone_and_locale() -> None:
    """Set the current user's timezone and locale automatically if required."""
    user = current_auth.user
    if (
        user.auto_timezone
        or not user.timezone
        or str(user.timezone).lower() not in valid_timezones
    ):
        if request.cookies.get('timezone'):
            cookie_timezone = unquote(request.cookies['timezone']).lower()
            remapped_timezone = valid_timezones.get(cookie_timezone)
            if remapped_timezone is not None:
                user.timezone = remapped_timezone  # type: ignore[assignment]
    if user.auto_locale or not user.locale or str(user.locale) not in supported_locales:
        user.locale = (  # pyright: ignore[reportAttributeAccessIssue]
            request.accept_languages.best_match(  # type: ignore[assignment]
                supported_locales.keys()
            )
            or 'en'
        )


def progressive_rate_limit_validator(
    token: str, prev_token: str | None
) -> tuple[bool, bool]:
    """
    Validate for :func:`validate_rate_limit` on autocomplete-type resources.

    Will count progressive keystrokes and backspacing as a single rate limited call, but
    any edits will be counted as a separate call, incrementing the resource usage count.

    :returns: tuple of (bool, bool): (count_this_call, retain_previous_token)
    """
    # prev_token will be None on the first call to the validator. Count the first
    # call, but don't retain the previous token
    if prev_token is None:
        return True, False

    # User is typing, so current token is previous token plus extra chars. Don't
    # count this as a new call, and keep the longer current token as the reference
    if token.startswith(prev_token):
        return False, False

    # User is backspacing (current < previous), so keep the previous token as the
    # reference in case they retype the deleted characters
    if prev_token.startswith(token):
        return False, True

    # Current token is differing from previous token, meaning this is a new query.
    # Increment the counter, discard previous token and use current token as ref
    return True, False


def validate_rate_limit(
    resource: str,
    identifier: str,
    attempts: int,
    timeout: int,
    token: str | None = None,
    validator: Callable[[str, str | None], tuple[bool, bool]] | None = None,
) -> None:
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
    # meaning it can contain just about any character and any length. The identifier is
    # hashed using BLAKE2b here to bring it down to a meaningful length. It is not
    # reversible should that be needed for debugging, but the obvious alternative Base64
    # encoding (for converting to 7-bit ASCII) cannot be used as it does not limit
    # length
    statsd.set(
        'rate_limit',
        blake2b(identifier.encode(), digest_size=32).hexdigest(),
        rate=1,
        tags={'resource': resource},
    )
    cache_key = f'rate_limit/v1/{resource}/{identifier}'
    cache_value: tuple[int, str] | None = cache.get(cache_key)
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
TEXT_TOKEN_PREFIX = 'temp_token/v1/'  # nosec


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


def retrieve_cached_token(token: str) -> dict | None:
    """Retrieve cached data given a token generated using :func:`make_cached_token`."""
    return cache.get(TEXT_TOKEN_PREFIX + token)


def delete_cached_token(token: str) -> bool:
    """Delete cached data for a token generated using :func:`make_cached_token`."""
    return cache.delete(TEXT_TOKEN_PREFIX + token)


# `compress` and `decompress` are typed to accept ``| str`` because `compress_response`
# calls with an `str` type, not a literal string


def compress(data: bytes, algorithm: Literal['br', 'gzip', 'deflate'] | str) -> bytes:
    """
    Compress data using Gzip, Deflate or Brotli.

    :param algorithm: One of ``br``, ``gzip`` or ``deflate``
    """
    match algorithm:
        case 'gzip':
            return gzip.compress(data)
        case 'deflate':
            return zlib.compress(data)
        case 'br':
            return brotli.compress(data)
    raise ValueError(f"Unknown compression algorithm: {algorithm}")


def decompress(data: bytes, algorithm: Literal['br', 'gzip', 'deflate'] | str) -> bytes:
    """
    Uncompress data using Gzip, Deflate or Brotli.

    :param algorithm: One of ``br``, ``gzip`` or ``deflate``
    """
    match algorithm:
        case 'gzip':
            return gzip.decompress(data)
        case 'deflate':
            return zlib.decompress(data)
        case 'br':
            return brotli.decompress(data)
    raise ValueError(f"Unknown compression algorithm: {algorithm}")


def compress_response(response: BaseResponse) -> None:
    """
    Conditionally compress a response based on request parameters.

    This function should ideally be used with a cache layer, such as
    :func:`~funnel.views.decorators.etag_cache_for_user`.
    """
    if (  # pylint: disable=too-many-boolean-expressions
        not response.direct_passthrough
        and response.content_length is not None
        and response.content_length > 500
        and 200 <= response.status_code < 300
        and 'Content-Encoding' not in response.headers
        and response.mimetype is not None
        and (
            response.mimetype.startswith('text/')
            or response.mimetype
            in ('application/json', 'application/javascript', 'application/x.html+json')
        )
    ):
        algorithm = request.accept_encodings.best_match(('br', 'gzip', 'deflate'))
        if algorithm is not None:
            response.set_data(compress(response.get_data(), algorithm))
            response.headers['Content-Encoding'] = algorithm
            response.vary.add('Accept-Encoding')


# MARK: Template helpers ---------------------------------------------------------------


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
        )
    if request_wants.json:
        response = jsonify({'status': 'error', 'error': 'redirect', 'location': url})
        response.status_code = 422
        response.headers['HX-Redirect'] = url
        return response
    return redirect(url, code)


def html_in_json(
    template: str,
) -> dict[str, str | Callable[[Mapping[str, Any]], ReturnView]]:
    """
    Render a HTML fragment in a JSON wrapper, for use with ``@render_with``.

    ::

        @render_with(html_in_json('template.html.jinja2'))
        def my_view(...) -> ReturnRenderWith: ...
    """

    def render_json_with_status(kwargs: Mapping[str, Any]) -> ReturnResponse:
        """Render plain JSON."""
        return jsonify(
            status='ok',
            **{
                k: (
                    v
                    if not isinstance(v, RoleMixin)
                    else v.current_access(datasets=('primary',))
                )
                for k, v in kwargs.items()
            },
        )

    def render_html_in_json(kwargs: Mapping[str, Any]) -> ReturnResponse:
        """Render HTML fragment in JSON."""
        resp = jsonify({'status': 'ok', 'html': render_template(template, **kwargs)})
        resp.content_type = 'application/x.html+json; charset=utf-8'
        return resp

    return {
        'text/html': template,
        'application/json': render_json_with_status,
        'application/x.html+json': render_html_in_json,
    }


# MARK: Filters and URL constructors ---------------------------------------------------


@app.template_filter('url_join')
def url_join(base: str, url: str = '') -> str:
    """Join URLs in a template filter."""
    return urljoin(base, url)


@app.template_filter('cleanurl')
def cleanurl_filter(url: str | furl) -> str:
    """Clean a URL in a template filter."""
    if not isinstance(url, furl):
        url = furl(url)
    url.path.normalize()
    # Strip leading and trailing slashes in //hostname/path/ to get hostname/path
    return furl().set(netloc=url.netloc, path=url.path).url.strip('/')


@app.template_filter('shortlink')
def shortlink(url: str, actor: Account | None = None, shorter: bool = True) -> str:
    """
    Return a short link suitable for sharing, in a template filter.

    Caller must perform a database commit.

    :param shorter: Use a shorter shortlink, ideal for SMS or a small database
    """
    sl = Shortlink.new(url, reuse=True, shorter=shorter, actor=actor)
    db.session.add(sl)
    g.require_db_commit = True
    return app_url_for(shortlinkapp, 'link', name=sl.name, _external=True)


# MARK: Request/response handlers ------------------------------------------------------


@app.before_request
def no_null_in_form() -> None:
    """Disallow NULL characters in any form submit (but don't scan file attachments)."""
    if request.method == 'POST':
        for values in request.form.listvalues():
            for each in values:
                if each is not None and '\x00' in each:
                    abort(400)


@app.after_request
def commit_db_session(response: ResponseType) -> ResponseType:
    """Commit database session at the end of a request if asked to."""
    # This handler is primarily required for the `|shortlink` template filter, which
    # may make a database entry in a view's ``return render_template(...)`` call and
    # is therefore too late for a commit within the view
    if g.get('require_db_commit', False):
        db.session.commit()
    return response


@app.after_request
def cache_expiry_headers(response: ResponseType) -> ResponseType:
    if response.expires is None:
        response.expires = nocache_expires
    if not response.cache_control.max_age:
        response.cache_control.max_age = 0
    return response
