"""View helpers."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import blake2b
from os import urandom
from typing import Any, Callable, Dict, Generic, Optional, Tuple, Type, TypeVar, Union
from urllib.parse import unquote, urljoin, urlsplit
import gzip
import zlib

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.routing import BuildError
from werkzeug.urls import url_quote
from werkzeug.wrappers import Response as ResponseBase

from furl import furl
from pytz import common_timezones
from pytz import timezone as pytz_timezone
from pytz import utc
import brotli

from baseframe import _, cache, statsd
from coaster.sqlalchemy import RoleMixin
from coaster.utils import newpin, require_one_of, utcnow

from .. import app, built_assets, shortlinkapp
from ..forms import supported_locales
from ..models import (
    EmailAddress,
    Shortlink,
    SMSMessage,
    User,
    UserEmail,
    UserEmailClaim,
    UserPhone,
    db,
    profanity,
)
from ..proxies import request_wants
from ..signals import emailaddress_refcount_dropping
from ..transports import TransportConnectionError, TransportRecipientError, sms
from ..typing import ReturnView
from ..utils import blake2b160_hex
from .jobs import forget_email

valid_timezones = set(common_timezones)

nocache_expires = utc.localize(datetime(1990, 1, 1))

# Six avatar colours defined in _variable.scss
avatar_color_count = 6

# --- Classes --------------------------------------------------------------------------


class OtpTimeoutError(Exception):
    """Exception to indicate the OTP has expired."""


class OtpReasonError(Exception):
    """OTP is being used for a different reason than originally intended."""


class SessionTimeouts(Dict[str, timedelta]):
    """
    Singleton dictionary that aids tracking timestamps in session.

    Use the :attr:`session_timeouts` instance instead of this class.
    """

    def __init__(self, *args, **kwargs):
        """Create a dictionary that separately tracks {key}_at keys."""
        super().__init__(*args, **kwargs)
        self.keys_at = {f'{key}_at' for key in self.keys()}

    def __setitem__(self, key: str, value: timedelta):
        """Add or set a value to the dictionary."""
        if key in self:
            raise KeyError(f"Key {key} is already present")
        if not isinstance(value, timedelta):
            raise ValueError("Value must be a timedelta")
        self.keys_at.add(f'{key}_at')
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        """Remove a value from the dictionary."""
        self.keys_at.remove(f'{key}_at')
        return super().__delitem__(key)

    def has_intersection(self, other):
        """Check for intersection with other dictionary-like object."""
        okeys = other.keys()
        return not (self.keys_at.isdisjoint(okeys) and self.keys().isdisjoint(okeys))


#: Temporary values that must be periodically expunged from the cookie session
session_timeouts = SessionTimeouts()
session_timeouts['otp'] = timedelta(minutes=15)


#: Tell mypy that the type of ``OtpSession.user`` is same as ``OtpSession.make(user)``.
#: We need both ``User`` and ``Optional[User]`` so that the value of ``loginform.user``
#: can be passed to :meth:`OtpSession.make`. This usage is documented in PEP 484:
#: https://peps.python.org/pep-0484/#user-defined-generic-types
OptionalUserType = TypeVar('OptionalUserType', User, Optional[User])


@dataclass
class OtpSession(Generic[OptionalUserType]):
    """Make or retrieve an OTP in the user's cookie session."""

    reason: str
    token: str
    otp: str
    user: OptionalUserType
    email: Optional[str] = None
    phone: Optional[str] = None

    @classmethod
    def make(  # pylint: disable=too-many-arguments
        cls: Type[OtpSession],
        reason: str,
        user: OptionalUserType,
        anchor: Optional[Union[UserEmail, UserEmailClaim, UserPhone, EmailAddress]],
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> OtpSession:
        """
        Create an OTP for login and save it to cache and browser cookie session.

        Accepts an anchor or an explicit email address or phone number.
        """
        # Safety check, only one of anchor, email and phone can be provided
        require_one_of(anchor=anchor, email=email, phone=phone)
        # Make an OTP valid for 15 minutes. Store this OTP in Redis cache and add a ref
        # to this cache entry in the user's cookie session. The cookie never contains
        # the actual OTP. See :func:`make_cached_token` for additional documentation.
        otp = newpin()
        if isinstance(anchor, (UserEmail, UserEmailClaim, EmailAddress)):
            email = str(anchor)
        elif isinstance(anchor, UserPhone):
            phone = str(anchor)
        # Allow 3 OTP requests per hour per anchor. This is distinct from the rate
        # limiting for password-based login above.
        validate_rate_limit(
            'otp-send',
            ('anchor/' + blake2b160_hex(email or phone)),  # type: ignore[arg-type]
            3,
            3600,
        )
        token = make_cached_token(
            {
                'reason': reason,
                'otp': otp,
                'user_buid': user.buid if user is not None else None,
                'email': email,
                'phone': phone,
            },
            timeout=15 * 60,
        )
        session['otp'] = token
        return cls(
            reason=reason, token=token, otp=otp, user=user, email=email, phone=phone
        )

    @classmethod
    def retrieve(cls: Type[OtpSession], reason: str) -> OtpSession:
        """Retrieve an OTP from cache using the token in browser cookie session."""
        otp_token = session.get('otp')
        if not otp_token:
            raise OtpTimeoutError('cookie_expired')
        otp_data = retrieve_cached_token(otp_token)
        if not otp_data:
            raise OtpTimeoutError('cache_expired')
        if otp_data['reason'] != reason:
            raise OtpReasonError(reason)
        return cls(
            reason=reason,
            token=otp_token,
            otp=otp_data['otp'],
            user=User.get(buid=otp_data['user_buid'])
            if otp_data['user_buid']
            else None,
            email=otp_data['email'],
            phone=otp_data['phone'],
        )

    @staticmethod
    def delete() -> bool:
        """Delete OTP request from cookie session and cache."""
        token = session.pop('otp', None)
        if not token:
            return False
        delete_cached_token(token)
        return True


# --- Utilities ------------------------------------------------------------------------


def metarefresh_redirect(url: str):
    """Redirect using a ``Meta: Refresh`` HTML header."""
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
        result += f'#{url_quote(_anchor)}'
    return result


def mask_email(email: str) -> str:
    """
    Masks an email address to obfuscate it while (hopefully) keeping it recognisable.

    >>> mask_email('foobar@example.com')
    'foo***@example.com'
    >>> mask_email('not-email')
    'not-em***'
    """
    if '@' not in email:
        return f'{email[:-3]}***'
    username, domain = email.split('@')
    return f'{username[:-3]}***@{domain}'


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


def validate_rate_limit(
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
    cache_value: Optional[Tuple[int, str]] = cache.get(cache_key)
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
    return cache.get(TEXT_TOKEN_PREFIX + token)


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


def compress_response(response: ResponseBase) -> None:
    """
    Conditionally compress a response based on request parameters.

    This function should ideally be used with a cache layer, such as
    :func:`~funnel.views.decorators.etag_cache_for_user`.
    """
    if (
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


def send_sms_otp(
    phone: str, otp: str, render_flash: bool = True
) -> Optional[SMSMessage]:
    """Send an OTP via SMS to a phone number."""
    template_message = sms.WebOtpTemplate(
        otp=otp,
        # TODO: Replace helpline_text with a report URL
        helpline_text=f"call {app.config['SITE_SUPPORT_PHONE']}",
        domain=current_app.config['SERVER_NAME'],
    )
    msg = SMSMessage(phone_number=phone, message=str(template_message))
    try:
        # Now send this
        msg.transactionid = sms.send(phone=msg.phone_number, message=template_message)
    except TransportRecipientError as exc:
        if render_flash:
            flash(str(exc), 'error')
    except TransportConnectionError:
        if render_flash:
            flash(_("Unable to send a message right now. Try again later"), 'error')
    else:
        # Commit only if an SMS could be sent
        db.session.add(msg)
        db.session.commit()
        if render_flash:
            flash(_("An OTP has been sent to your phone number"), 'success')
        return msg
    return None


# --- Template helpers -----------------------------------------------------------------


def render_redirect(url: str, code: int = 302) -> ResponseBase:
    """Render a redirect that is sensitive to the request type."""
    if request_wants.html_fragment:
        return Response(
            render_template('redirect.html.jinja2', url=url),
            status=200,
            headers={'HX-Redirect': url},
        )
    return redirect(url, code)


def html_in_json(template: str) -> Dict[str, Union[str, Callable[[dict], ReturnView]]]:
    """Render a HTML fragment in a JSON wrapper, for use with ``@render_with``."""

    def render_json_with_status(kwargs) -> ResponseBase:
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

    def render_html_in_json(kwargs) -> ResponseBase:
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
    return urljoin(base, url)


@app.template_filter('cleanurl')
def cleanurl_filter(url):
    if not isinstance(url, furl):
        url = furl(url)
    url.path.normalize()
    # Strip leading and trailing slashes in //hostname/path/ to get hostname/path
    return furl().set(netloc=url.netloc, path=url.path).url.strip('/')


@app.template_filter('shortlink')
def shortlink(url, actor=None):
    """Return a short link suitable for SMS. Caller must perform a database commit."""
    sl = Shortlink.new(url, reuse=True, shorter=True, actor=actor)
    db.session.add(sl)
    return app_url_for(shortlinkapp, 'link', name=sl.name, _external=True)


def built_asset(assetname):
    return built_assets[assetname]


@app.context_processor
def template_context() -> Dict[str, Any]:
    """Add template context items."""
    return {'built_asset': built_asset}


# --- Request/response handlers --------------------------------------------------------


@app.after_request
def track_temporary_session_vars(response):
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
def cache_expiry_headers(response):
    if response.expires is None:
        response.expires = nocache_expires
    if not response.cache_control.max_age:
        response.cache_control.max_age = 0
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
def forget_email_in_background_job(response):
    if hasattr(g, 'forget_email_hashes'):
        for email_hash in g.forget_email_hashes:
            forget_email.queue(email_hash)
    return response
