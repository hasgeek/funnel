"""Provides the request_wants proxy for views and templates."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from flask import (  # type: ignore[attr-defined]
    Response,
    _request_ctx_stack,
    has_request_context,
    request,
)
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

__all__ = ['request_wants']

TestFunc = TypeVar('TestFunc', bound=Callable[['RequestWants'], Any])


class TestUses:
    """
    Identify HTTP headers accessed in this test, to be set in the response Vary header.

    This decorator is for use in :class:`RequestWants`, and converts the decorated
    method into a cached property.
    """

    def __init__(self, *headers: str) -> None:
        self.headers = headers

    def __call__(self, f: TestFunc) -> TestFunc:
        headers = self.headers

        @wraps(f)
        def wrapper(self: RequestWants) -> Any:
            self.response_vary.update(headers)
            if not has_request_context():
                return False
            return f(self)

        return cast(TestFunc, cached_property(wrapper))


class RequestWants:
    """
    Holding class for tests on what the current request wants in a response.

    Each test is implemented as a `cached_property` returning a `bool` or `str`. The
    test also updates :attr:`response_vary` with the headers that were accessed. The
    view must set a ``Vary`` header in the response with the contents of
    ``request_wants.response_vary``. This is automated via :func:`response_varies`,
    which is registered as an `after_request` handler by
    :func:`~funnel.proxies.init_app`.
    """

    def __init__(self):
        self.response_vary = set()

    def __bool__(self):
        return has_request_context()

    # --- request_wants tests ----------------------------------------------------------

    @TestUses('Accept')
    def json(self) -> bool:
        """Request wants a JSON response."""
        return request.accept_mimetypes.best == 'application/json'

    @TestUses('X-Requested-With', 'Accept', 'HX-Request')
    def html_fragment(self) -> bool:
        """Request wants a HTML fragment for embedding (XHR or HTMX)."""
        return request.accept_mimetypes.best in (
            None,  # No Accept header
            '*/*',  # Default for jQuery and HTMX requests
            'text/html',  # HTML mimetype
            'application/x.html+json',  # Custom mimetype for Funnel
        ) and (
            request.environ.get('HTTP_HX_REQUEST', '') == 'true'
            or request.environ.get('HTTP_X_REQUESTED_WITH', '').lower()
            == 'xmlhttprequest'
        )

    @TestUses('Accept')
    def html_in_json(self) -> bool:
        """Request wants HTML embedded in JSON (custom type for this project)."""
        return (
            request.accept_mimetypes.best_match(
                ('red/herring', 'application/x.html+json')
            )
            == 'application/x.html+json'
        )

    @TestUses('HX-Request')
    def htmx(self) -> bool:
        """Request wants a HTMX-compatible response."""
        return request.environ.get('HTTP_HX_REQUEST') == 'true'

    @TestUses('HX-Trigger')
    def hx_trigger(self) -> Optional[str]:
        """Id of element that triggered a HTMX request."""
        return request.environ.get('HTTP_HX_TRIGGER')

    @TestUses('HX-Trigger-Name')
    def hx_trigger_name(self) -> Optional[str]:
        """Name of element that triggered a HTMX request."""
        return request.environ.get('HTTP_HX_TRIGGER_NAME')

    @TestUses('HX-Target')
    def hx_target(self) -> Optional[str]:
        """Target of a HTMX request."""
        return request.environ.get('HTTP_HX_TARGET')

    @TestUses('HX-Prompt')
    def hx_prompt(self) -> Optional[str]:
        """Content of user prompt in HTMX."""
        return request.environ.get('HTTP_HX_PROMPT')

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
