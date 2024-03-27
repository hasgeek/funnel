"""View decorator utility functions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from functools import wraps
from hashlib import blake2b
from typing import Any, Literal

from flask import Response, current_app, make_response, request, url_for
from redis.lock import Lock as RedisLock

from baseframe import cache, statsd

from .. import redis_store
from ..auth import current_auth
from ..proxies import request_wants
from ..typing import P, ReturnResponse, ReturnView, T
from .helpers import compress_response, render_redirect


def xml_response(f: Callable[P, str]) -> Callable[P, Response]:
    """Wrap the view result in a :class:`Response` with XML mimetype."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Response:
        return Response(f(*args, **kwargs), mimetype='application/xml')

    return wrapper


def xhr_only(
    redirect_to: str | Callable[[], str] | None = None
) -> Callable[[Callable[P, T]], Callable[P, T | ReturnResponse]]:
    """Render a view only when it's an XHR request."""

    def decorator(f: Callable[P, T]) -> Callable[P, T | ReturnResponse]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | ReturnResponse:
            if not request_wants.html_fragment:
                if redirect_to is None:
                    destination = url_for('index')
                elif callable(redirect_to):
                    destination = redirect_to()
                else:
                    destination = redirect_to
                return render_redirect(
                    destination, 302 if request.method == 'GET' else 303
                )
            return f(*args, **kwargs)

        return wrapper

    return decorator


def etag_cache_for_user(
    identifier: str,
    view_version: int,
    timeout: int,
    max_age: int | None = None,
    query_params: set | None = None,
) -> Callable[[Callable[P, ReturnView]], Callable[P, ReturnView]]:
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

    def decorator(f: Callable[P, ReturnView]) -> Callable[P, ReturnView]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> ReturnView:
            # No ETag or cache storage if the request is not GET or HEAD
            if request.method not in ('GET', 'HEAD'):
                return f(*args, **kwargs)

            cache_key = f'{identifier}/{view_version}/{current_auth.user.uuid_b64}'

            # 1. Create a hash representing the state of the request, to ensure we're
            # sending a response appropriate for this request

            # Hash of request args, query parameters and common headers that influence
            # output. May need to be expanded to also add headers from Vary (which must
            # be specified in the decorator)
            request_hash = blake2b(
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
            # for each distinct request_hash. Look for the one matching our request_hash

            cache_data: dict[str, Any] | None = cache.get(cache_key)
            response_data: bytes | None = None
            status_code: int | None = None
            etag: str | None = None
            content_encoding: str | None = None
            content_type: str | None = None
            last_modified: datetime | None = None
            if cache_data:
                rhash_data = cache_data.get(request_hash, {})
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
                response.vary.add('Accept-Encoding')
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
                    f'/{chash}/{request_hash}'.encode()
                ).hexdigest()
                last_modified = datetime.utcnow()
                cache_data[request_hash] = {
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
            if etag is not None:
                response.set_etag(etag)
            if last_modified is not None:
                response.last_modified = last_modified
            response.cache_control.max_age = max_age
            response.expires = (
                response.last_modified or datetime.utcnow()
            ) + timedelta(seconds=max_age)

            return response.make_conditional(request)

        return wrapper

    return decorator


def idempotent_request(
    methods: Sequence[Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE']] = (
        'POST',
        'PUT',
        'PATCH',
        'DELETE',
    ),
    timeout: int | float = 10,
) -> Callable[[Callable[P, ReturnView]], Callable[P, ReturnView]]:
    """
    Make a submit request idempotent using a cache, gracefully handling dupe requests.

    :param methods: HTTP methods to apply to; the default list has common non-idempotent
        methods, but some requests may need this on GET too
    :param timeout: Timeout period for cache, in seconds
    """

    def decorator(f: Callable[P, ReturnView]) -> Callable[P, ReturnView]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> ReturnView:
            if request.method not in methods:
                return f(*args, **kwargs)
            statsd.incr(
                'idempotent_request',
                tags={'endpoint': request.endpoint, 'stage': 'call'},
            )
            # 1. Create a hash fingerprinting the request, with whatever is expected to
            #    be common to a dupe request caused by a double click
            request_hash = blake2b(
                '\n'.join(
                    [
                        request.method,
                        request.url,  # This includes all view args and query parameters
                        request.headers.get('Accept') or '',
                        request.headers.get('X-Requested-With') or '',
                        request.headers.get('HX-Request') or '',
                    ]
                    # Render these dicts as string representations before hashing
                    + [f'{_k}={_v}' for _k, _v in request.form.items(multi=True)]
                    + [f'{_k}={_v}' for _k, _v in request.cookies.items(multi=True)]
                    + [
                        f'{_k}={_v.filename}'
                        for _k, _v in request.files.items(multi=True)
                    ]
                ).encode()
            ).hexdigest()
            # Include current_auth-processed actor id and request endpoint as debugging
            # identifiers, since the actual content of the request including the URL is
            # hashed
            actor_id = current_auth.actor.uuid_b64 if current_auth else '-'
            cache_key = f'idempotent/{request.endpoint}/{actor_id}/{request_hash}'
            # 2. Acquire a Redis lock on this cache key
            #    from cache
            redis_lock = RedisLock(
                # FlaskRedis is a proxy to Redis, so the type mismatch can be ignored
                redis_store,  # pyright: ignore[reportArgumentType]
                f'lock/{cache_key}',
                timeout=timeout,
                blocking_timeout=timeout,
            )
            with redis_lock:
                # 3. Now that we have a lock, check if there is existing data in cache
                response = cache.get(cache_key)
                if response is not None:
                    if isinstance(response, Response):
                        # We caught a dupe request
                        statsd.incr(
                            'idempotent_request',
                            tags={'endpoint': request.endpoint, 'stage': 'hit'},
                        )
                        # Dupe requests should be intercepted client-side, with the
                        # server-side interception as backup. Log as `warning` so it
                        # comes to attention, but consider downgrading to `info` later
                        current_app.logger.warning(
                            "Dupe request intercepted and served from cache: %s",
                            cache_key,
                        )
                        response.headers['X-Cache'] = 'HIT'
                        return response
                    # Malformed cache result: log an error as this shouldn't happen
                    statsd.incr(
                        'idempotent_request',
                        tags={'endpoint': request.endpoint, 'stage': 'error'},
                    )
                    current_app.logger.error(
                        "Idempotent request found malformed data in cache: %s",
                        response,
                    )

                # 4. If the cache was unusable (missing, malformed), call the view and
                #    cache the response
                response = make_response(f(*args, **kwargs))
                response.freeze()
                redis_lock.reacquire()  # Reset TTL for the Redis lock's key
                cache.set(cache_key, response, timeout=timeout)
                response.headers['X-Cache'] = 'MISS'
                statsd.incr(
                    'idempotent_request',
                    tags={'endpoint': request.endpoint, 'stage': 'miss'},
                )
                return response

        return wrapper

    return decorator
