"""Support for development and testing environments."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, NamedTuple, Optional, Tuple
import atexit
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
from .typing import ReturnView

__all__ = ['AppByHostWsgi', 'BackgroundWorker', 'devtest_app']

# Force 'fork' on macOS. The default mode of 'spawn' (from py38) causes a pickling
# error in py39, as reported in pytest-flask:
# https://github.com/pytest-dev/pytest-flask/pull/138
# https://github.com/pytest-dev/pytest-flask/issues/139
if platform.system() == 'Darwin':
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    multiprocessing = multiprocessing.get_context('fork')  # type: ignore[assignment]

# --- Development and testing app multiplexer ------------------------------------------

info_app = Flask(__name__)


@info_app.route('/', endpoint='index')
@info_app.route('/<path:_ignore_path>')
def info_index(_ignore_path: str = '') -> ReturnView:
    """Info app provides a guide to access the server."""
    info = "Add the following entries to /etc/hosts to access:\n\n"
    max_host_len = max(len(host) for host in devtest_app.apps_by_host.keys())
    for host, app in devtest_app.apps_by_host.items():
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
        if not apps:
            raise ValueError("An app is required")
        for app in apps:
            if not app.config.get('SERVER_NAME'):
                raise ValueError(f"App does not have SERVER_NAME set: {app!r}")
        self.apps_by_host: Dict[str, Flask] = {
            app.config['SERVER_NAME'].split(':', 1)[0]: app for app in apps
        }

    @property
    def debug(self) -> bool:
        """Control debug flag on apps."""
        return any(app.debug for app in self.apps_by_host.values())

    @debug.setter
    def debug(self, value: bool) -> None:
        for app in self.apps_by_host.values():
            app.debug = value

    def get_app(self, host: str) -> Flask:
        """Get app matching a host."""
        if ':' in host:
            host = host.split(':', 1)[0]
        # Serve app that is a direct match for the host
        if host in self.apps_by_host:
            return self.apps_by_host[host]
        # Serve app that the host is a subdomain of
        for app_host, app in self.apps_by_host.items():
            if host.endswith('.' + app_host):
                return app
        # If no host matched, use the info app
        return info_app

    def __call__(self, environ, start_response) -> Iterable[bytes]:
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
        timeout: int = 10,
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

        engines = set()
        for app in main_app, shortlinkapp:  # TODO: Add hasjobapp here
            with app.app_context():
                engines.add(db.engines[None])
                for bind in app.config.get('SQLALCHEMY_BINDS') or ():
                    engines.add(db.engines[bind])
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
            # If another process is running at the same port, the connection will
            # succeed but our process may have exited. Check for that
            if not self._process.is_alive():
                raise RuntimeError(f"Server exited with code {self._process.exitcode}")

    def _is_ready(self) -> bool:
        """Probe for readyness with a socket connection."""
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

    def _stop_cleanly(self) -> bool:
        """
        Attempt to stop the server cleanly.

        Sends a SIGINT signal and waits for ``timeout`` seconds.

        :return: True if the server was cleanly stopped, False otherwise.
        """
        if (
            self._process is None
            or not self._process.pid
            or not self._process.is_alive()
        ):
            # Process is not running
            return True
        os.kill(self._process.pid, signal.SIGINT)
        self._process.join(self.timeout)
        # Exitcode will be None if process has not terminated
        return self._process.exitcode is not None

    def __repr__(self) -> str:
        if self.probe_at:
            return (
                f"<BackgroundWorker with pid {self.pid} listening at"
                f" {self.probe_at.host}:{self.probe_at.port}>"
            )
        return f"<BackgroundWorker with pid {self.pid}>"
