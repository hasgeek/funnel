from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import Response, current_app, g, redirect, request

from .. import app, funnelapp
from ..models import db

# https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
F = TypeVar('F', bound=Callable[..., Any])


def legacy_redirect(f: F) -> F:
    """
    Redirects legacy profiles to ``funnelapp`` and other profiles to ``app``, based on
    the value of ``Profile.legacy``. This flag is True for profiles originally served
    from talkfunnel.com that are still pending migration to hasgeek.com (due end-2020).

    Ref: https://github.com/hasgeek/funnel/issues/230 (last item in checklist)
    """

    @wraps(f)
    def wrapper(classview, **kwargs):
        if g.profile and request.method == 'GET':
            if g.profile.legacy and current_app._get_current_object() is app:
                with funnelapp.app_context(), funnelapp.test_request_context():
                    return redirect(
                        classview.obj.url_for(
                            classview.current_handler.name, _external=True
                        ),
                        code=303,
                    )
            elif (
                not g.profile.legacy and current_app._get_current_object() is funnelapp
            ):
                with app.app_context(), app.test_request_context():
                    return redirect(
                        classview.obj.url_for(
                            classview.current_handler.name, _external=True
                        ),
                        code=303,
                    )
        return f(classview, **kwargs)

    return cast(F, wrapper)


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
    def wrapper(*args, **kwargs) -> Response:
        try:
            result = f(*args, **kwargs)
        finally:
            db.session.remove()
        return result

    return cast(F, wrapper)
