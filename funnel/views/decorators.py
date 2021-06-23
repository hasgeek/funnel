from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, Union, cast

from flask import Response, redirect, url_for

from baseframe import request_is_xhr

from ..models import db
from ..typing import ReturnView

# https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
F = TypeVar('F', bound=Callable[..., Any])


def xml_response(f: F) -> F:
    """Wrap the view result in a :class:`Response` with XML mimetype."""

    @wraps(f)
    def wrapper(*args, **kwargs) -> Response:
        return Response(f(*args, **kwargs), mimetype='application/xml')

    return cast(F, wrapper)


def remove_db_session(f: F) -> F:
    """
    Remove the database session after calling the wrapped function.

    A transaction error in a background job will affect future queries, so the
    transaction must be rolled back.

    Required until this underlying issue is resolved:
    https://github.com/dchevell/flask-executor/issues/15
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> ReturnView:
        try:
            result = f(*args, **kwargs)
        finally:
            db.session.remove()
        return result

    return cast(F, wrapper)


def xhr_only(redirect_to: Union[str, Callable[[], str], None] = None):
    """Render a view only when it's an XHR request."""

    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs) -> ReturnView:
            if not request_is_xhr():
                if redirect_to is None:
                    destination = url_for('index')
                elif callable(redirect_to):
                    destination = redirect_to()
                else:
                    destination = redirect_to
                return redirect(destination)
            return f(*args, **kwargs)

        return cast(F, wrapper)

    return decorator
