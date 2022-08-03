"""Support for development and testing environments."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Tuple
import atexit
import logging
import multiprocessing
import os
import platform
import signal
import socket
import time

from sqlalchemy.engine import Engine

from flask import Flask

from . import app as main_app
from . import shortlinkapp
from .models import db

__all__ = ['AppByHostWsgi', 'BackgroundWorker', 'devtest_app']

# Force 'fork' on macOS. The default mode of 'spawn' (from py38) causes a pickling
# error in py39, as reported in pytest-flask:
# https://github.com/pytest-dev/pytest-flask/pull/138
# https://github.com/pytest-dev/pytest-flask/issues/139
if platform.system() == 'Darwin':
    multiprocessing = multiprocessing.get_context('fork')  # type: ignore[assignment]

# --- Development and testing app multiplexer ------------------------------------------

info_app = Flask(__name__)


@info_app.route('/', endpoint='index')
@info_app.route('/<path:_ignore_path>')
def info_index(_ignore_path: str = ''):
    """Info app provides a guide to access the server."""
    info = "Add the following entries to /etc/hosts to access:\n\n"
    max_host_len = max(len(host) for host, app in devtest_app.apps_by_host)
    for host, app in devtest_app.apps_by_host:
        space_padding = ' ' * (max_host_len - len(host) + 2)
        info += (
            f"127.0.0.1\t{host}{space_padding}"
            f"# {app.config['PREFERRED_URL_SCHEME']}://{app.config['SERVER_NAME']}/\n"
        )
    return info, 200, {'Content-Type': 'text/plain; charset=utf-8'}


class AppByHostWsgi:
    """
    WSGI app multiplexer that invokes the app matching the host name.

    Subdomains are assumed to be hosted by the matching app, but if an app claims to
    host the subdomain of another app, it is given priority.
    """

    def __init__(self, *apps: Flask) -> None:
        # If we have apps where one serves a subdomain of another, sort them so that
        # the subdomain is first.
        if not apps:
            raise ValueError("One app is required")
        for app in apps:
            if not app.config.get('SERVER_NAME'):
                raise ValueError(f"App does not have SERVER_NAME set: {app!r}")

        self.apps_by_host: List[Tuple[str, Flask]] = sorted(
            (
                (app.config['SERVER_NAME'].split(':', 1)[0], app)
                for app in apps
                if app.config.get('SERVER_NAME')
            ),
            key=lambda host_and_app: host_and_app[0].split('.')[::-1],
            reverse=True,
        )

    def get_app(self, host: str) -> Flask:
        """Get app matching a host."""
        if ':' in host:
            host = host.split(':', 1)[0]
        for app_host, app_for_host in self.apps_by_host:
            if host == app_host or host.endswith('.' + app_host):  # For subdomains
                return app_for_host

        # If no host matched, use the info app
        return info_app

    def __call__(self, environ, start_response):
        use_app = self.get_app(environ['HTTP_HOST'])
        return use_app(environ, start_response)


devtest_app = AppByHostWsgi(main_app, shortlinkapp)

# --- Background worker ----------------------------------------------------------------


class HostPort(NamedTuple):
    """Host and port to probe for a ready server."""

    host: str
    port: int


def _dispose_engines_in_child_process(
    engines: Iterable[Engine],
    worker: Callable,
    args: Tuple[Any],
    kwargs: Dict[str, Any],
) -> Any:
    """Dispose SQLAlchemy engine connections in a forked process."""
    # https://docs.sqlalchemy.org/en/14/core/pooling.html#pooling-multiprocessing
    for e in engines:
        e.dispose(close=False)  # type: ignore[call-arg]
    return worker(*args, **kwargs)


# Adapted from pytest-flask's LiveServer
class BackgroundWorker:
    """
    Launch a worker in a background process.

    :param worker: The worker to run
    :param args: Args for worker
    :param kwargs: Kwargs for worker
    :param probe: Optional host and port to probe for ready state
    :param timeout: Timeout after which launch is considered to have failed
    :param clean_stop: Ask for graceful shutdown (default yes)
    :param daemon: Run process in daemon mode (linked to parent, automatic shutdown)
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        worker: Callable,
        args: Optional[Iterable] = None,
        kwargs: Optional[dict] = None,
        probe_at: Optional[Tuple[str, int]] = None,
        timeout: int = 30,
        clean_stop=True,
        daemon=True,
    ) -> None:
        self.worker = worker
        self.worker_args = args or ()
        self.worker_kwargs = kwargs or {}
        self.probe_at = HostPort(*probe_at) if probe_at else None
        self.timeout = timeout
        self.clean_stop = clean_stop
        self.daemon = daemon
        self._process: Optional[multiprocessing.Process] = None

    def start(self) -> None:
        """Start worker in a separate process."""
        if self._process is not None:
            return

        engines = {
            db.get_engine(app, bind)
            # TODO: Add hasjobapp here
            for app in (main_app, shortlinkapp)
            for bind in ([None] + list(app.config.get('SQLALCHEMY_BINDS') or ()))
        }
        self._process = multiprocessing.Process(
            target=_dispose_engines_in_child_process,
            args=(engines, self.worker, self.worker_args, self.worker_kwargs),
        )
        self._process.daemon = self.daemon
        self._process.start()
        # Ensure shutdown at exit in case caller forgets to call .stop()
        atexit.register(self.stop)
        if self.probe_at:
            keep_trying = True
            start_time = time.time()
            while keep_trying:
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    raise RuntimeError(
                        f"Failed to confirm server start after {self.timeout} seconds"
                    )
                if self._is_ready():
                    keep_trying = False

    def _is_ready(self) -> bool:
        if not self.probe_at:
            return False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(self.probe_at)
        except OSError:
            ret = False
        else:
            ret = True
        finally:
            sock.close()
        return ret

    @property
    def pid(self) -> Optional[int]:
        """PID of background worker."""
        return self._process.pid if self._process else None

    def stop(self) -> None:
        """Stop background worker."""
        atexit.unregister(self.stop)
        if self._process:
            if self.clean_stop and self._stop_cleanly():
                return
            if self._process.is_alive():
                # If it's still alive, kill it
                self._process.terminate()
            self._process.close()
            self._process = None

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
        if self.probe_at:
            return (
                f"<BackgroundWorker with pid {self.pid} listening at"
                f" {self.probe_at.host}:{self.probe_at.port}>"
            )
        return f"<BackgroundWorker with pid {self.pid}>"
