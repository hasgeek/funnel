"""Provides the request_wants proxy for views and templates."""
from __future__ import annotations

from functools import wraps
from typing import Callable, cast

from flask import (  # type: ignore[attr-defined]
    Response,
    _request_ctx_stack,
    has_request_context,
    request,
)
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

__all__ = ['request_wants']


def test_uses(*headers: str):
    """
    Identify HTTP headers accessed in this test, to be set in the response Vary header.

    This decorator is for use in :class:`RequestWants`, and converts the decorated
    method into a cached property.
    """

    def decorator(f: Callable[[RequestWants], bool]) -> Callable[[RequestWants], bool]:
        @wraps(f)
        def inner(self: RequestWants) -> bool:
            self.response_vary.update(headers)
            if not has_request_context():
                return False
            return f(self)

        return cast(Callable[['RequestWants'], bool], cached_property(inner))

    return decorator


class RequestWants:
    """
    Holding class for tests on the sort of response the current request wants.

    Each test is implemented as a `cached_property` that returns a boolean. The test
    also updates :attr:`response_vary` with the headers that were accessed. The view
    must set a ``Vary`` header in the response with the contents of
    ``request_wants.response_vary``.
    """

    def __init__(self):
        self.response_vary = set()

    def __bool__(self):
        return has_request_context()

    # --- request_wants tests ----------------------------------------------------------

    @test_uses('Accept')
    def json(self) -> bool:
        """Request wants a JSON response."""
        return request.accept_mimetypes.best == 'application/json'

    @test_uses('X-Requested-With', 'Accept', 'HX-Request', 'HX-Target')
    def html_fragment(self) -> bool:
        """Request wants a HTML fragment for embedding (XHR or HTMX)."""
        return (
            request.environ.get('HTTP_HX_REQUEST', '') == 'true'
            and request.environ.get('HTTP_HX_TARGET', '') != ''
        ) or (
            request.environ.get('HTTP_X_REQUESTED_WITH', '').lower() == 'xmlhttprequest'
            and request.accept_mimetypes.best
            in (
                None,  # No Accept header
                '*/*',  # Default for jQuery requests
                'text/html',  # HTML mimetype
                'application/x.html+json',  # Custom mimetype for Funnel
            )
        )

    @test_uses('Accept')
    def html_in_json(self) -> bool:
        """Request wants HTML embedded in JSON (custom type for this project)."""
        return (
            request.accept_mimetypes.best_match(
                ('red/herring', 'application/x.html+json')
            )
            == 'application/x.html+json'
        )

    @test_uses('HX-Request')
    def htmx(self) -> bool:
        """Request wants a HTMX-compatible response."""
        return request.environ.get('HTTP_HX_REQUEST', '') == 'true'

    # --- End of request_wants tests ---------------------------------------------------


def _get_request_wants() -> RequestWants:
    if has_request_context():
        wants = getattr(_request_ctx_stack.top, 'request_wants', None)
        if wants is None:
            wants = _request_ctx_stack.top.request_wants = RequestWants()
        return wants
    # Return an empty handler
    return RequestWants()


request_wants = LocalProxy(_get_request_wants)


def response_varies(response: Response) -> Response:
    """App ``after_request`` handler to set response ``Vary`` header."""
    response.vary.update(request_wants.response_vary)  # type: ignore[union-attr]
    return response
