"""Provides the request_wants proxy for views and templates."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, TypeVar, cast

from flask import has_request_context, request
from flask.globals import request_ctx
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

from ..typing import ResponseType, T

__all__ = ['RequestWants', 'request_wants']


RequestWantsType = TypeVar('RequestWantsType', bound='RequestWants')


def test_uses(
    *headers: str,
) -> Callable[
    [Callable[[RequestWantsType], T]],  # pyright: ignore[reportInvalidTypeVarUse]
    cached_property[T | None],
]:
    """
    Identify HTTP headers accessed in this test, to be set in the response Vary header.

    This decorator is for use in :class:`RequestWants`, and converts the decorated
    method into a cached property.
    """

    def decorator(f: Callable[[RequestWantsType], T]) -> cached_property[T | None]:
        @wraps(f)
        def wrapper(self: RequestWantsType) -> T | None:
            self.response_vary.update(headers)
            if not has_request_context():
                return None
            return f(self)

        return cached_property(wrapper)

    return decorator


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

    def __init__(self) -> None:
        self.response_vary: set[str] = set()

    def __bool__(self) -> bool:
        return has_request_context()

    # MARK: request_wants tests --------------------------------------------------------

    @test_uses('Accept')
    def json(self) -> bool:
        """Request wants a JSON response."""
        return request.accept_mimetypes.best == 'application/json'

    @test_uses('Accept', 'HX-Request', 'X-Requested-With')
    def html_fragment(self) -> bool:
        """Request wants a HTML fragment for embedding (XHR or HTMX)."""
        return request.accept_mimetypes.best in (
            'text/x.fragment+html',  # HTML fragment (custom)
            'application/x.html+json',  # HTML fragment in a JSON wrapper (custom)
        ) or (
            request.accept_mimetypes.best
            in (
                None,  # No Accept header
                '*/*',  # Default for jQuery and HTMX requests
                'text/html',  # HTML mimetype
                'text/x.embed+html',  # HTML fragment
                'application/x.html+json',  # Custom mimetype for Funnel
            )
            and (
                request.environ.get('HTTP_HX_REQUEST', '') == 'true'
                or request.environ.get('HTTP_X_REQUESTED_WITH', '').lower()
                == 'xmlhttprequest'
            )
        )

    @test_uses('Accept')
    def html_in_json(self) -> bool:
        """Request wants HTML embedded in JSON (custom type for this project)."""
        return request.accept_mimetypes.best == 'application/x.html+json'

    @test_uses('HX-Request')
    def htmx(self) -> bool:
        """Request wants a HTMX-compatible response."""
        return request.environ.get('HTTP_HX_REQUEST') == 'true'

    @test_uses('HX-Trigger')
    def hx_trigger(self) -> str | None:
        """Id of element that triggered a HTMX request."""
        return request.environ.get('HTTP_HX_TRIGGER')

    @test_uses('HX-Trigger-Name')
    def hx_trigger_name(self) -> str | None:
        """Name of element that triggered a HTMX request."""
        return request.environ.get('HTTP_HX_TRIGGER_NAME')

    @test_uses('HX-Target')
    def hx_target(self) -> str | None:
        """Target of a HTMX request."""
        return request.environ.get('HTTP_HX_TARGET')

    @test_uses('HX-Prompt')
    def hx_prompt(self) -> str | None:
        """Content of user prompt in HTMX."""
        return request.environ.get('HTTP_HX_PROMPT')

    # MARK: End of request_wants tests -------------------------------------------------

    if TYPE_CHECKING:

        def _get_current_object(self) -> RequestWants:
            """Type hint for the LocalProxy wrapper method."""
            return self


def _get_request_wants() -> RequestWants:
    """Get request_wants from the request."""
    if has_request_context():
        # pylint: disable=protected-access
        wants = getattr(request_ctx, 'request_wants', None)
        if wants is None:
            wants = RequestWants()
            request_ctx.request_wants = wants  # type: ignore[attr-defined]
        return wants
    # Return an empty handler
    return RequestWants()


request_wants: RequestWants = cast(RequestWants, LocalProxy(_get_request_wants))


def response_varies(response: ResponseType) -> ResponseType:
    """App ``after_request`` handler to set response ``Vary`` header."""
    response.vary.update(request_wants.response_vary)
    return response
