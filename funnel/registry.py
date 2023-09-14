"""Resource registry."""

from __future__ import annotations

import re
from collections import OrderedDict
from collections.abc import Callable, Collection
from dataclasses import dataclass
from functools import wraps
from typing import Any, NoReturn

from flask import Response, abort, jsonify, request
from werkzeug.datastructures import MultiDict

from baseframe import _
from baseframe.signals import exception_catchall

from .models import AccountExternalId, AuthToken
from .typing import P, ReturnResponse

# Bearer token, as per
# http://tools.ietf.org/html/draft-ietf-oauth-v2-bearer-15#section-2.1
auth_bearer_re = re.compile('^Bearer ([a-zA-Z0-9_.~+/-]+=*)$')


class ResourceRegistry(OrderedDict):
    """Dictionary of resources."""

    def resource(
        self,
        name: str,
        description: str | None = None,
        trusted: bool = False,
        scope: str | None = None,
    ) -> Callable[[Callable[P, Any]], Callable[[], ReturnResponse]]:
        """
        Decorate a resource function.

        :param str name: Name of the resource
        :param str description: User-friendly description
        :param bool trusted: Restrict access to trusted clients?
        :param str scope: Grant access via this other resource name (which must also
            exist)
        """
        usescope = scope or name
        if '*' in usescope or ' ' in usescope:
            # Don't allow resources to be declared with '*' or ' ' in the name
            raise ValueError(usescope)

        def resource_auth_error(message: str) -> Response:
            return Response(
                message,
                401,
                {
                    'WWW-Authenticate': (
                        f'Bearer realm="Token Required" scope="{usescope}"'
                    )
                },
            )

        def decorator(
            f: Callable[[AuthToken, MultiDict, MultiDict], Any]
        ) -> Callable[[], ReturnResponse]:
            @wraps(f)
            def wrapper() -> ReturnResponse:
                if request.method == 'GET':
                    args = request.args
                elif request.method in ['POST', 'PUT', 'DELETE']:
                    args = request.form
                else:
                    abort(405)
                if 'Authorization' in request.headers:
                    token_match = auth_bearer_re.search(
                        request.headers['Authorization']
                    )
                    if token_match is not None:
                        token = token_match.group(1)
                    else:
                        # Unrecognized Authorization header
                        return resource_auth_error(
                            _("A Bearer token is required in the Authorization header")
                        )
                else:
                    # No token provided in Authorization header
                    return resource_auth_error(
                        _("An access token is required to access this resource")
                    )
                authtoken = AuthToken.get(token=token)
                if authtoken is None:
                    return resource_auth_error(_("Unknown access token"))
                if not authtoken.is_valid():
                    return resource_auth_error(_("Access token has expired"))

                # Read once to avoid reparsing below
                tokenscope = set(authtoken.effective_scope)
                wildcardscope = usescope.split('/', 1)[0] + '/*'
                if not (authtoken.auth_client.trusted and '*' in tokenscope):
                    # If a trusted client has '*' in token scope, all good,
                    # else check further
                    if (usescope not in tokenscope) and (
                        wildcardscope not in tokenscope
                    ):
                        # Client doesn't have access to this scope either
                        # directly or via a wildcard
                        return resource_auth_error(
                            _("Token does not provide access to this resource")
                        )
                if trusted and not authtoken.auth_client.trusted:
                    return resource_auth_error(
                        _("This resource can only be accessed by trusted clients")
                    )
                # All good. Return the result value
                try:
                    result = f(authtoken, args, request.files)
                    response = jsonify({'status': 'ok', 'result': result})
                except Exception as exc:  # noqa: B902  # pylint: disable=broad-except
                    exception_catchall.send(exc)
                    response = jsonify(
                        {
                            'status': 'error',
                            'error': exc.__class__.__name__,
                            'error_description': str(exc),
                        }
                    )
                    response.status_code = 500
                # XXX: Let resources control how they return?
                response.headers[
                    'Cache-Control'
                ] = 'no-cache, no-store, max-age=0, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                return response

            self[name] = {
                'name': name,
                'scope': usescope,
                'description': description,
                'trusted': trusted,
                'f': f,
            }
            return wrapper

        return decorator


@dataclass
class LoginProviderData:
    """User data supplied by a LoginProvider."""

    userid: str
    username: str | None = None
    avatar_url: str | None = None
    oauth_token: str | None = None
    oauth_token_secret: str | None = None  # Only used in OAuth1a
    oauth_token_type: str | None = None
    oauth_refresh_token: str | None = None
    oauth_expires_in: int | None = None
    email: str | None = None
    emails: Collection[str] = ()
    emailclaim: str | None = None
    phone: str | None = None
    fullname: str | None = None


class LoginProviderRegistry(OrderedDict):
    """Registry of login providers."""

    def at_username_services(self) -> list[str]:
        """Return services which typically use ``@username`` addressing."""
        return [key for key in self if self[key].at_username]

    def at_login_items(self) -> list[tuple[str, LoginProvider]]:
        """Return services which have the flag at_login set to True."""
        return [(k, v) for (k, v) in self.items() if v.at_login is True]

    def __setitem__(self, key: str, value: LoginProvider) -> None:
        """Make a registry entry."""
        super().__setitem__(key, value)
        AccountExternalId.__at_username_services__ = self.at_username_services()

    def __delitem__(self, key: str) -> None:
        """Remove a registry entry."""
        super().__delitem__(key)
        AccountExternalId.__at_username_services__ = self.at_username_services()


class LoginError(Exception):
    """External service login failure."""


class LoginInitError(LoginError):
    """External service login failure (during init)."""


class LoginCallbackError(LoginError):
    """External service login failure (during callback)."""


class LoginProvider:
    """
    Base class for login providers.

    Each implementation provides two methods: :meth:`do` and :meth:`callback`.
    :meth:`do` is called when the user chooses to login with the specified provider.
    :meth:`callback` is called with the response from the provider.

    Both :meth:`do` and :meth:`callback` are called as part of a Flask
    view and have full access to the view infrastructure. However, while
    :meth:`do` is expected to return a Response to the user,
    :meth:`callback` only returns information on the user back to Lastuser.

    Implementations must take their configuration via the __init__
    constructor.

    :param name: Name of the service (stored in the database)
    :param title: Title (shown to user)
    :param at_login: (default True). Is this service available to the user for login? If
        `False`, it can only be added from the user's account settings. Use this for
        add-on services (for example, Zoom).
    :param bool priority: (default False). Is this service high priority? If False,
        it'll be hidden behind a show more link.
    :param str icon: URL to icon for login provider.
    """

    #: This service's usernames are typically
    #: used for addressing with @username
    at_username = False

    def __init__(
        self,
        name: str,
        title: str,
        key: str,
        secret: str,
        at_login: bool = True,
        icon: str | None = None,
        **kwargs,
    ) -> None:
        self.name = name
        self.title = title
        self.key = key
        self.secret = secret
        self.at_login = at_login
        self.icon = icon
        for k, v in kwargs.items():
            setattr(self, k, v)

    def do(self, callback_url: str) -> NoReturn:
        """Initiate a login with this login provider."""
        raise NotImplementedError

    def callback(self) -> LoginProviderData:
        """Process callback from login provider."""
        raise NotImplementedError

        # Template for subclasses. All optional values can be skipped
        # return LoginProviderData(
        #     userid=None,  # Unique user id at this service
        #     username=None,  # Public username. This may change
        #     avatar_url=None,  # URL to avatar image
        #     oauth_token=None,  # OAuth token, for OAuth-based services
        #     oauth_token_secret=None,  # If required
        #     oauth_token_type=None,  # Type of token
        #     email=None,  # Verified email address. Service can be trusted
        #     emailclaim=None,  # Claimed email address. Must be verified
        #     phone=None,  # Verified phone number when service can be trusted
        # )


# Global registries
resource_registry = ResourceRegistry()
login_registry = LoginProviderRegistry()
