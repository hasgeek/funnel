"""Support for development and testing environments."""
# pyright: reportGeneralTypeIssues=false

from __future__ import annotations

import atexit
import gc
import inspect
import multiprocessing
import os
import signal
import socket
import time
import weakref
from collections.abc import Callable, Iterable
from secrets import token_urlsafe
from typing import Any, NamedTuple, Protocol, cast

from flask import Flask

from . import all_apps, app as main_app, transports
from .models import db
from .typing import ReturnView

__all__ = ['AppByHostWsgi', 'BackgroundWorker', 'devtest_app']

# Devtest requires `fork`. The default `spawn` method on macOS and Windows will
# cause pickling errors all over. `fork` is unavailable on Windows, so
# :class:`BackgroundWorker` can't be used there either, affecting `devserver.py` and the
# Pytest `live_server` fixture used for end-to-end tests. Fork on macOS is not
# compatible with the Objective C framework. If you have a framework Python build and
# experience crashes, try setting the environment variable
# `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`
mpcontext = multiprocessing.get_context('fork')

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
        self.apps_by_host: dict[str, Flask] = {
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

    def __call__(self, environ: Any, start_response: Any) -> Iterable[bytes]:
        use_app = self.get_app(environ['HTTP_HOST'])
        return use_app(environ, start_response)


devtest_app = AppByHostWsgi(*all_apps)

# --- Background worker ----------------------------------------------------------------


class HostPort(NamedTuple):
    """Host and port to probe for a ready server."""

    host: str
    port: int


class CapturedSms(NamedTuple):
    phone: str
    message: str
    vars: dict[str, str]  # noqa: A003


class CapturedEmail(NamedTuple):
    subject: str
    to: list[str]
    content: str
    from_email: str | None


class CapturedCalls(Protocol):
    """Protocol class for captured calls."""

    email: list[CapturedEmail]
    sms: list[CapturedSms]


def _signature_without_annotations(func) -> inspect.Signature:
    """Generate a function signature without parameter type annotations."""
    sig = inspect.signature(func)
    return sig.replace(
        parameters=[
            p.replace(annotation=inspect.Parameter.empty)
            for p in sig.parameters.values()
        ]
    )


def install_mock(func: Any, mock: Any) -> None:
    """
    Patch all existing references to :attr:`func` with :attr:`mock`.

    Uses the Python garbage collector to find and replace all references.
    """
    # Validate function signature match before patching, ignoring type annotations
    fsig = _signature_without_annotations(func)
    msig = _signature_without_annotations(mock)
    if fsig != msig:
        raise TypeError(
            f"Mock function’s signature does not match original’s:\n"
            f"{mock.__name__}{msig} !=\n"
            f"{func.__name__}{fsig}"
        )
    # Use weakref to dereference func from local namespace
    func = weakref.ref(func)
    gc.collect()
    refs = gc.get_referrers(func())
    # Recover func from the weakref so we can do an `is` match in referrers
    func = func()
    for ref in refs:
        if isinstance(ref, dict):
            # We have a namespace dict. Iterate through contents to find the reference
            # and replace it
            for key, value in ref.items():
                if value is func:
                    ref[key] = mock
        else:
            raise RuntimeError(
                f"Can't patch {func.__qualname__} in unknown reference type {ref!r}"
            )


def _prepare_subprocess(
    mock_transports: bool,
    calls: CapturedCalls,
    worker: Callable,
    args: tuple[Any],
    kwargs: dict[str, Any],
) -> Any:
    """
    Prepare a subprocess for hosting a worker.

    1. Dispose all SQLAlchemy engine connections so they're not shared with the parent
    2. Mock transports if requested, redirecting all calls to a log
    3. Launch the worker
    """
    # https://docs.sqlalchemy.org/en/20/core/pooling.html#pooling-multiprocessing
    with main_app.app_context():
        for engine in db.engines.values():
            engine.dispose(close=False)

    if mock_transports:

        def mock_email(
            subject: str,
            to: list[Any],
            content: str,
            attachments=None,
            from_email: Any | None = None,
            headers: dict | None = None,
            base_url: str | None = None,
        ) -> str:
            capture = CapturedEmail(
                subject,
                [str(each) for each in to],
                content,
                str(from_email) if from_email else None,
            )
            calls.email.append(capture)
            main_app.logger.info(capture)
            return token_urlsafe()

        def mock_sms(
            phone: Any,
            message: transports.sms.SmsTemplate,
            callback: bool = True,
        ) -> str:
            capture = CapturedSms(str(phone), str(message), message.vars())
            calls.sms.append(capture)
            main_app.logger.info(capture)
            return token_urlsafe()

        # Patch email
        install_mock(transports.email.send.send_email, mock_email)
        # Patch SMS
        install_mock(transports.sms.send.send_sms, mock_sms)

    return worker(*args, **kwargs)


# Adapted from pytest-flask's LiveServer
class BackgroundWorker:
    """
    Launch a worker in a background process.

    :param worker: The worker to run
    :param args: Args for worker
    :param kwargs: Kwargs for worker
    :param probe_at: Optional tuple of (host, port) to probe for ready state
    :param timeout: Timeout after which launch is considered to have failed
    :param clean_stop: Ask for graceful shutdown (default yes)
    :param daemon: Run process in daemon mode (linked to parent, automatic shutdown)
    :param mock_transports: Patch transports with mock functions that write to a log
    """

    def __init__(
        self,
        worker: Callable,
        args: Iterable | None = None,
        kwargs: dict | None = None,
        probe_at: tuple[str, int] | None = None,
        timeout: int = 10,
        clean_stop: bool = True,
        daemon: bool = True,
        mock_transports: bool = False,
    ) -> None:
        self.worker = worker
        self.worker_args = args or ()
        self.worker_kwargs = kwargs or {}
        self.probe_at = HostPort(*probe_at) if probe_at else None
        self.timeout = timeout
        self.clean_stop = clean_stop
        self.daemon = daemon
        self._process: multiprocessing.context.ForkProcess | None = None
        self.mock_transports = mock_transports

        manager = mpcontext.Manager()
        self.calls = cast(CapturedCalls, manager.Namespace())
        self.calls.email = cast(list[CapturedEmail], manager.list())
        self.calls.sms = cast(list[CapturedSms], manager.list())

    def start(self) -> None:
        """Start worker in a separate process."""
        if self._process is not None:
            return

        self._process = mpcontext.Process(
            target=_prepare_subprocess,
            args=(
                self.mock_transports,
                self.calls,
                self.worker,
                self.worker_args,
                self.worker_kwargs,
            ),
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
        """Probe for readiness with a socket connection."""
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
    def pid(self) -> int | None:
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

        Sends a SIGINT signal and waits for :attr:`timeout` seconds.

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

    def __enter__(self) -> BackgroundWorker:
        """Start server in a context manager."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Finalise a context manager."""
        self.stop()
