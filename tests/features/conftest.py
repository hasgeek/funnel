"""Feature test configuration."""

from __future__ import annotations

from types import SimpleNamespace

from werkzeug import run_simple

from pytest_splinter.webdriver_patches import patch_webdriver
from selenium import webdriver
import pytest

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
    # Use HTTPS for live server (set to False if required)
    use_https = True
    scheme = 'https' if use_https else 'http'
    # Use app's port from SERVER_NAME as basis for the port to run the live server on
    port_str = app.config['SERVER_NAME'].partition(':')[-1]
    if not port_str or not port_str.isdigit():
        pytest.fail(
            f"App does not have SERVER_NAME specified as host:port in config:"
            f" {app.config['SERVER_NAME']}"
        )
    port = int(port_str)

    # Save app config before modifying it to match live server environment
    original_app_config = {}
    for m_app in devtest_app.apps_by_host.values():
        original_app_config[m_app] = {
            'PREFERRED_URL_SCHEME': m_app.config['PREFERRED_URL_SCHEME'],
            'SERVER_NAME': m_app.config['SERVER_NAME'],
        }
        m_app.config['PREFERRED_URL_SCHEME'] = scheme
        m_host = m_app.config['SERVER_NAME'].split(':', 1)[0]
        m_app.config['SERVER_NAME'] = f'{m_host}:{port}'

    # Start background worker and wait until it's receiving connections
    server = BackgroundWorker(
        run_simple,
        args=('127.0.0.1', port, devtest_app),
        kwargs={
            'use_reloader': False,
            'use_debugger': True,
            'use_evalex': False,
            'threaded': True,
            'ssl_context': 'adhoc' if use_https else None,
        },
        probe_at=('127.0.0.1', port),
    )
    try:
        server.start()
    except RuntimeError as exc:
        # Server did not respond to probe until timeout; mark test as failed
        server.stop()
        pytest.fail(str(exc))

    with app.app_context():
        # Return live server config within an app context so that the test function
        # can use url_for without creating a context. However, secondary apps will
        # need context specifically established for url_for on them
        yield SimpleNamespace(
            url=f'{scheme}://{app.config["SERVER_NAME"]}/',
            urls=[
                f'{scheme}://{m_app.config["SERVER_NAME"]}/'
                for m_app in devtest_app.apps_by_host.values()
            ],
        )

    # Stop server after use
    server.stop()

    # Restore original app config
    for m_app, config in original_app_config.items():
        m_app.config.update(config)


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate
