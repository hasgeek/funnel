from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps
from hashlib import blake2b
from typing import Any, Callable, Optional, Set, TypeVar, Union, cast

from flask import Response, make_response, redirect, request, url_for

from baseframe import cache, request_is_xhr
from coaster.auth import current_auth

from ..models import db
from ..typing import ReturnView
from .helpers import compress_response

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


def etag_cache_for_user(
    identifier: str,
    view_version: int,
    timeout: int,
    max_age: Optional[int] = None,
    query_params: Optional[Set] = None,
):
    """
    Cache and compress a response, and add an ETag header for browser cache.

    :param identifier: Distinct name for this view (typically same as endpoint name)
    :param view_version: A version number for this view. Increment when templates change
    :param timeout: Maximum age for server cache in seconds
    :param max_age: Maximum age for client cache in seconds, defaults to same as timeout
    :param query_params: Request query parameters that influence response
    """
    if max_age is None:
        max_age = timeout

    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Response:
            # No ETag or cache storage if the request is not GET or HEAD
            if request.method not in ('GET', 'HEAD'):
                return f(*args, **kwargs)

            cache_key = f'{identifier}/{view_version}/{current_auth.user.uuid_b64}'

            # 1. Create a hash representing the state of the request, to ensure we're
            # sending a response appropriate for this request

            # Hash of request args, query parameters and common headers that influence
            # output. May need to be expanded to also add headers from Vary (which must
            # be specified in the decorator)
            rhash = blake2b(
                '\n'.join(
                    [
                        request.headers.get('Accept', ''),
                        request.headers.get('Accept-Language', ''),
                        request.headers.get('Accept-Encoding', ''),
                        request.headers.get('X-Requested-With', ''),
                        request.endpoint or '',
                    ]
                    + [
                        f'{_key}={_value}'
                        for _key, _value in sorted((request.view_args or {}).items())
                    ]
                    + (
                        [
                            qp + '=' + str(request.args.getlist(qp))
                            for qp in query_params
                        ]
                        if query_params is not None
                        else []
                    )
                ).encode()
            ).hexdigest()

            # 2. Get existing data from cache. There may be multiple copies of data,
            # for each distinct rhash. Look for the one matching our rhash
            cache_data = cache.get(cache_key)
            response_data = None
            if cache_data:
                rhash_data = cache_data.get(rhash, {})
                try:
                    response_data = rhash_data['response_data']
                    content_encoding = rhash_data['content_encoding']
                    chash = rhash_data['chash']
                    etag = rhash_data['etag']
                    last_modified = rhash_data['last_modified']
                    status_code = rhash_data['status_code']
                    content_type = rhash_data['content_type']
                except KeyError:
                    # If any of the required cache keys are missing, discard the cache
                    response_data = None
            else:
                cache_data = {}

            if response_data is not None:
                # 3a. If the cache had valid data (not expired, not malformed), use it
                # for a response.
                response = Response(
                    response_data,
                    status=status_code,
                    content_type=content_type,
                )
                if content_encoding:
                    response.headers['Content-Encoding'] = content_encoding
                response.vary.add('Accept-Encoding')  # type: ignore[union-attr]
            else:
                # 3b. If the cache was unusable (missing, malformed), call the view to
                # to get a fresh response and put it in the cache.
                response = make_response(f(*args, **kwargs))
                # Compress the response to stop Nginx from resetting ETag
                compress_response(response)
                response_data = response.get_data()
                content_encoding = response.headers.get('Content-Encoding')
                chash = blake2b(response.get_data()).hexdigest()
                etag = blake2b(
                    f'{identifier}/{view_version}/{current_auth.user.uuid_b64}'
                    f'/{chash}/{rhash}'.encode()
                ).hexdigest()
                last_modified = datetime.utcnow()
                cache_data[rhash] = {
                    'response_data': response_data,
                    'content_encoding': content_encoding,
                    'cash': chash,
                    'etag': etag,
                    'last_modified': last_modified,
                    'status_code': response.status_code,
                    'content_type': response.content_type,
                }
                cache.set(
                    cache_key,
                    cache_data,
                    timeout=timeout,
                )
            response.set_etag(etag)
            response.last_modified = last_modified
            response.cache_control.max_age = max_age
            response.expires = (
                response.last_modified or datetime.utcnow()
            ) + timedelta(seconds=cast(int, max_age))

            # mypy errors:
            # 1. error: Incompatible return value type (got
            #    "werkzeug.wrappers.response.Response", expected
            #    "flask.wrappers.Response") [return-value]
            # 2. error: Argument 1 to "make_conditional" of "Response" has incompatible
            #    type "Request"; expected "Dict[str, Any]"  [arg-type]
            return response.make_conditional(request)  # type: ignore[return-value,arg-type]

        return cast(F, wrapper)

    return decorator
