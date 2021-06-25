from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps
from hashlib import blake2b
from typing import Any, Callable, TypeVar, Union, cast

from flask import Response, make_response, redirect, request, url_for

from baseframe import cache, request_is_xhr
from coaster.auth import current_auth

from ..models import db
from ..typing import ReturnView
from .helpers import compress

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


def etag_cache_for_user(identifier: str, template_version: int, max_age: int):
    """Cache and compress a response, and add an ETag header for browser cache."""

    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Response:
            # No ETag or cache storage if the request is not GET or HEAD
            if request.method not in ('GET', 'HEAD'):
                return f(*args, **kwargs)

            cache_key = f'{identifier}/{template_version}/{current_auth.user.uuid_b64}'
            rendered_content = None
            # Hash of (common) headers that influence output. May need to be expanded
            # to also add headers from Vary (which must be specified in the decorator)
            hhash = blake2b(
                '\n'.join(
                    [
                        request.headers.get('Accept', ''),
                        request.headers.get('Accept-Language', ''),
                        request.headers.get('Accept-Encoding', ''),
                        request.headers.get('X-Requested-With', ''),
                    ]
                ).encode()
            ).hexdigest()

            cache_data = cache.get(cache_key)
            if cache_data:
                try:
                    rendered_content = cache_data['rendered_content']
                    chash = cache_data['blake2b']
                    etag = cache_data['etag']
                    last_modified = cache_data['last_modified']
                    status_code = cache_data['status_code']
                    content_type = cache_data['content_type']
                    if (
                        etag
                        != blake2b(
                            f'{current_auth.user.uuid_b64}/{chash}/{hhash}'.encode()
                        ).hexdigest()
                    ):
                        rendered_content = None
                except KeyError:
                    # If any of the required cache keys are missing, discard the cache
                    rendered_content = None
            if rendered_content is not None:
                response = Response(
                    rendered_content,
                    status=status_code,
                    content_type=content_type,
                )
            else:
                response = make_response(f(*args, **kwargs))
                rendered_content = response.get_data(True)
                chash = blake2b(response.get_data()).hexdigest()
                etag = blake2b(
                    f'{current_auth.user.uuid_b64}/{chash}/{hhash}'.encode()
                ).hexdigest()
                last_modified = datetime.utcnow()
                cache.set(
                    cache_key,
                    {
                        'rendered_content': rendered_content,
                        'blake2b': chash,
                        'etag': etag,
                        'last_modified': last_modified,
                        'status_code': response.status_code,
                        'content_type': response.content_type,
                    },
                    timeout=max_age,
                )
            response.set_etag(etag)
            response.last_modified = last_modified
            response.cache_control.max_age = max_age
            response.expires = (
                response.last_modified or datetime.utcnow()
            ) + timedelta(seconds=max_age)

            # Compress the response to stop Nginx from resetting ETag
            if (
                response.content_length is not None
                and response.content_length > 500
                and 200 <= response.status_code < 300
                and 'Content-Encoding' not in response.headers
                and response.mimetype
                in (
                    'text/plain',
                    'text/html',
                    'text/css',
                    'text/xml',
                    'application/json',
                    'application/javascript',
                )
            ):
                algorithm = request.accept_encodings.best_match(
                    ('br', 'gzip', 'deflate')
                )
                if algorithm is not None:
                    response.set_data(compress(response.get_data(), algorithm))
                    response.headers['Content-Encoding'] = algorithm
                    response.vary.add('Accept-Encoding')  # type: ignore[union-attr]

            # mypy errors:
            # 1. error: Incompatible return value type (got
            #    "werkzeug.wrappers.response.Response", expected
            #    "flask.wrappers.Response") [return-value]
            # 2. error: Argument 1 to "make_conditional" of "Response" has incompatible
            #    type "Request"; expected "Dict[str, Any]"  [arg-type]
            return response.make_conditional(request)  # type: ignore[return-value,arg-type]

        return cast(F, wrapper)

    return decorator
