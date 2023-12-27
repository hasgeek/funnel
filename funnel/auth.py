"""Auth proxy."""

from coaster.auth import (
    CurrentAuth as CurrentAuthBase,
    GetCurrentAuth,
    add_auth_anchor,
    add_auth_attribute,
    request_has_auth,
)

from . import all_apps
from .models import User

__all__ = [
    'CurrentAuth',
    'add_auth_attribute',
    'add_auth_anchor',
    'current_auth',
    'request_has_auth',
]


class CurrentAuth(CurrentAuthBase):
    """CurrentAuth for Funnel."""

    # These attrs are typed as not-optional because they're typically accessed in a view
    # that is already gated with the `@requires_login` or related decorator, so they're
    # guaranteed to be present within the view. However, this will require a type-ignore
    # for any code that tests `if current_auth.actor`, so those will need a rewrite to
    # `if current_auth`. When auth clients become supported actors, this may need some
    # form of PEP 647 typeguard to identify the actor's exact type.

    user: User
    actor: User


current_auth = GetCurrentAuth.proxy(CurrentAuth)

# Install this proxy in all apps, overriding the proxy provided by coaster.app.init_app
for _app in all_apps:
    _app.jinja_env.globals['current_auth'] = current_auth
