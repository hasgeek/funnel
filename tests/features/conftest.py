"""Feature test configuration."""

from __future__ import annotations

from werkzeug import run_simple

from pytest_splinter.webdriver_patches import patch_webdriver
from selenium import webdriver
import pytest

from funnel import rq
from funnel.devtest import BackgroundWorker, devtest_app


@pytest.fixture(scope='session')
def browser_patches():  # noqa : PT004
    """Patch webdriver for pytest-splinter."""
    # Required due to https://github.com/pytest-dev/pytest-splinter/issues/158
    patch_webdriver()


@pytest.fixture(scope='session')
def splinter_driver_kwargs(splinter_webdriver):
    """Disable certification verification for webdriver."""
    if splinter_webdriver == 'chrome':
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')

        return {'options': options}
    return {}


@pytest.fixture(scope='package')
def live_server(request, database, app):
    """Run application in a separate process."""
    port = int(app.config['SERVER_NAME'].split(':', 1)[-1])
    for _m_host, m_app in devtest_app.apps_by_host:
        m_app.config['PREFERRED_URL_SCHEME'] = 'https'
    rq_server = BackgroundWorker(rq.get_worker().work)
    app_server = BackgroundWorker(
        run_simple,
        args=('127.0.0.1', port, devtest_app),
        kwargs={
            'use_reloader': False,
            'use_debugger': True,
            'use_evalex': False,
            'threaded': True,
            'ssl_context': 'adhoc',
        },
        probe_at=('127.0.0.1', port),
    )
    try:
        rq_server.start()
        app_server.start()
    except RuntimeError as exc:
        pytest.fail(str(exc))
    yield app_server
    app_server.stop()
    rq_server.stop()


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate
