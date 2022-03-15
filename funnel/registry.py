"""Resource registry."""

from __future__ import annotations

from collections import OrderedDict
from functools import wraps
from typing import List, NamedTuple, Optional, Tuple
import re

from flask import Response, abort, jsonify, request

from baseframe import _
from baseframe.signals import exception_catchall

from .models import AuthToken, UserExternalId

# Bearer token, as per
# http://tools.ietf.org/html/draft-ietf-oauth-v2-bearer-15#section-2.1
auth_bearer_re = re.compile('^Bearer ([a-zA-Z0-9_.~+/-]+=*)$')


class ResourceRegistry(OrderedDict):
    """Dictionary of resources."""

    def resource(
        self,
        name: str,
        description: Optional[str] = None,
        trusted: bool = False,
        scope: str = None,
    ):
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

        def resource_auth_error(message: str):
            return Response(
                message,
                401,
                {
                    'WWW-Authenticate': 'Bearer realm="Token Required" scope="%s"'
                    % usescope
                },
            )

        def wrapper(f):
            @wraps(f)
            def decorated_function():
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

                tokenscope = set(
                    authtoken.effective_scope
                )  # Read once to avoid reparsing below
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
                except Exception as exception:
                    exception_catchall.send(exception)
                    response = jsonify(
                        {
                            'status': 'error',
                            'error': exception.__class__.__name__,
                            'error_description': str(exception),
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
            return decorated_function

        return wrapper


class LoginProviderData(NamedTuple):
    """User data supplied by a LoginProvider."""

    userid: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    oauth_token: Optional[str] = None
    oauth_token_secret: Optional[str] = None  # Only used in OAuth1a
    oauth_token_type: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    oauth_refresh_expiry: Optional[str] = None
    email: Optional[str] = None
    emails: List[str] = []
    emailclaim: Optional[str] = None
    phone: Optional[str] = None
    phoneclaim: Optional[str] = None
    fullname: Optional[str] = None


class LoginProviderRegistry(OrderedDict):
    """Registry of login providers."""

    def at_username_services(self) -> List[str]:
        """Return services which typically use ``@username`` addressing."""
        return [key for key in self if self[key].at_username]

    def at_login_items(self) -> List[Tuple[str, LoginProvider]]:
        """Return services which have the flag at_login set to True."""
        return [(k, v) for (k, v) in self.items() if v.at_login is True]

    def __setitem__(self, key: str, value: LoginProvider):
        """Make a registry entry."""
        retval = super().__setitem__(key, value)
        UserExternalId.__at_username_services__ = self.at_username_services()
        return retval

    def __delitem__(self, key: str):
        """Remove a registry entry."""
        retval = super().__delitem__(key)
        UserExternalId.__at_username_services__ = self.at_username_services()
        return retval


class LoginError(Exception):
    """External service login failure."""


class LoginInitError(Exception):
    """External service login failure (during init)."""


class LoginCallbackError(Exception):
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
        false, it will only be available to be added in the user's profile page. Use
        this for multiple instances of the same external service with differing access
        permissions (for example, with Twitter).
    :param bool priority: (default False). Is this service high priority? If False,
        it'll be hidden behind a show more link.
    :param str icon: URL to icon for login provider.
    """

    #: URL to icon for the login button
    icon = None
    #: Login form, if required
    form = None
    #: This service's usernames are typically
    #: used for addressing with @username
    at_username = False

    def __init__(
        self,
        name: str,
        title: str,
        at_login: bool = True,
        priority: bool = False,
        icon: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.name = name
        self.title = title
        self.at_login = at_login
        self.priority = priority
        self.icon = icon

    def do(self, callback_url: str):
        raise NotImplementedError

    def callback(self) -> LoginProviderData:
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
        #     phoneclaim=None,  # Claimed phone number, needing verification
        # )


# Global registries
resource_registry = ResourceRegistry()
login_registry = LoginProviderRegistry()
