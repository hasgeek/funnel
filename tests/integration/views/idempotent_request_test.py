"""Tests for idempotent request decorator."""

# pylint: disable=redefined-outer-name

from collections.abc import Generator
from queue import Empty, SimpleQueue
from threading import Thread
from time import sleep

import pytest
import requests
from flask import Flask, request
from werkzeug.serving import make_server

from baseframe import baseframe

from funnel.views.decorators import idempotent_request


@pytest.fixture
def call_log() -> SimpleQueue:
    return SimpleQueue()


@pytest.fixture
def idempotent_test_app(call_log: SimpleQueue) -> Flask:
    app = Flask(__name__)
    app.config.from_prefixed_env()
    baseframe.init_app(app)  # The idempotent_request decorator needs baseframe config

    @app.route('/clear', methods=['GET', 'POST'])
    def clear() -> str:
        """Unwrapped route."""
        call_log.put((request.endpoint, request.method))
        sleep(0.2)
        return 'clear'

    @app.route('/iget')
    @idempotent_request(['GET'])
    def iget() -> str:
        """Idempotent GET."""
        call_log.put((request.endpoint, request.method))
        sleep(0.2)
        return 'get'

    @app.route('/igetpost', methods=['GET', 'POST'])
    @idempotent_request()
    def ipost() -> str:
        """Idempotent POST."""
        call_log.put((request.endpoint, request.method))
        sleep(0.2)
        return 'post'

    return app


@pytest.fixture
def _server(idempotent_test_app: Flask) -> Generator[None, None, None]:
    s = make_server('localhost', 3003, idempotent_test_app, threaded=True)
    t = Thread(target=s.serve_forever)
    t.start()
    yield
    s.shutdown()
    t.join(1)


# TODO: specify jitter type as a second parametrize decorator, replacing the flag here
@pytest.mark.parametrize(
    ('path', 'method', 'jitter', 'qsize', 'calls'),
    [
        ('clear', 'GET', False, 2, [('clear', 'GET'), ('clear', 'GET')]),
        ('clear', 'POST', False, 2, [('clear', 'POST'), ('clear', 'POST')]),
        ('iget', 'GET', False, 1, [('iget', 'GET')]),
        ('igetpost', 'GET', False, 2, [('ipost', 'GET'), ('ipost', 'GET')]),
        ('igetpost', 'POST', False, 1, [('ipost', 'POST')]),
        ('clear', 'GET', True, 2, [('clear', 'GET'), ('clear', 'GET')]),
        ('clear', 'POST', True, 2, [('clear', 'POST'), ('clear', 'POST')]),
        ('iget', 'GET', True, 2, [('iget', 'GET'), ('iget', 'GET')]),
        ('igetpost', 'GET', True, 2, [('ipost', 'GET'), ('ipost', 'GET')]),
        ('igetpost', 'POST', True, 2, [('ipost', 'POST'), ('ipost', 'POST')]),
    ],
)
@pytest.mark.usefixtures('_server', 'db_session')  # db_session clears Redis cache
def test_regular_route(
    call_log: SimpleQueue,
    path: str,  # Call this view path in the test app
    method: str,  # Use this HTTP method
    jitter: bool,  # Make each request distinct
    qsize: int,  # Count of calls received by the view
    calls: list[tuple[str, str]],  # Content of call log
) -> None:
    results: SimpleQueue[requests.Response] = SimpleQueue()

    def worker(num: int) -> None:
        results.put(
            requests.request(
                method,
                f'http://localhost:3003/{path}',
                params={'id': num},
                data={'data': num},
            )
        )

    t1 = Thread(target=worker, args=[1] if jitter else [0])
    t2 = Thread(target=worker, args=[2] if jitter else [0])
    t1.start()
    t2.start()
    t1.join(1)
    t2.join(1)
    assert not call_log.empty()
    assert call_log.qsize() == qsize
    all_calls = []
    try:
        while True:
            all_calls.append(call_log.get_nowait())
    except Empty:
        pass
    assert all_calls == calls
    all_results = []
    try:
        while True:
            all_results.append(results.get_nowait())
    except Empty:
        pass
    assert len(all_results) == 2
    # FIXME: Headers are missing in the response here, unclear why:

    # cache_status = [r.headers.get('X-Cache') for r in all_results]
    # if qsize == 2:
    #     assert cache_status in [['HIT', 'MISS'], ['MISS', 'HIT']]
    # else:
    #     assert cache_status == ['HIT', 'HIT']
