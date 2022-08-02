"""Feature test configuration."""

from __future__ import annotations

from typing import Optional
import logging
import multiprocessing
import os
import platform
import signal
import socket
import time

from werkzeug import run_simple

from pytest_splinter.webdriver_patches import patch_webdriver
from selenium import webdriver
import pytest

from funnel import devtest_app

# force 'fork' on macOS
if platform.system() == 'Darwin':
    multiprocessing = multiprocessing.get_context('fork')  # type: ignore[assignment]


# This code was adapted from pytest-flask and customised for Funnel's devtest_app which
# multiplexes multipe apps by host name
class LiveServer:
    """
    Helper class to launch a live server in a background process.

    :param app: The application to run.
    :param port: The port to run application.
    :param timeout: The timeout after which test case is aborted if
        application is not started.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self, app, port: int, timeout: int = 30, clean_stop=False, ssl_context=None
    ) -> None:
        self.app = app
        self.port = port
        self.timeout = timeout
        self.clean_stop = clean_stop
        self.ssl_context = ssl_context
        self._process: Optional[multiprocessing.Process] = None

    def start(self) -> None:
        """Start application in a separate process."""

        def worker(app, port: int) -> None:
            """Worker process for web server."""
            run_simple(
                '127.0.0.1',
                port,
                app,
                use_reloader=False,
                use_debugger=True,
                use_evalex=False,
                threaded=True,
                ssl_context=self.ssl_context,
            )

        self._process = multiprocessing.Process(
            target=worker, args=(self.app, self.port)
        )
        self._process.daemon = True
        self._process.start()

        keep_trying = True
        start_time = time.time()
        while keep_trying:
            elapsed_time = time.time() - start_time
            if elapsed_time > self.timeout:
                pytest.fail(f"Failed to start the server after {self.timeout} seconds.")
            if self._is_ready():
                keep_trying = False

    def _is_ready(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(('127.0.0.1', self.port))
        except OSError:
            ret = False
        else:
            ret = True
        finally:
            sock.close()
        return ret

    def stop(self) -> None:
        """Stop application process."""
        if self._process:
            if self.clean_stop and self._stop_cleanly():
                return
            if self._process.is_alive():
                # If it's still alive, kill it
                self._process.terminate()

    def _stop_cleanly(self, timeout: int = 5) -> bool:
        """
        Attempt to stop the server cleanly.

        Sends a SIGINT signal and waits for ``timeout`` seconds.

        :return: True if the server was cleanly stopped, False otherwise.
        """
        if not self._process or not self._process.pid:
            return True
        try:
            os.kill(self._process.pid, signal.SIGINT)
            self._process.join(timeout)
            return True
        except Exception:  # noqa: B902  # pylint: disable=broad-except
            logging.exception("Failed to join the live server process.")
            return False

    def __repr__(self) -> str:
        return f"<LiveServer listening at {self.port}>"


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
    server = LiveServer(devtest_app, port, clean_stop=True, ssl_context='adhoc')
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def db_session(db_session_truncate):
    """Use truncate mode for db session."""
    return db_session_truncate
