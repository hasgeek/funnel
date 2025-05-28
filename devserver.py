#!/usr/bin/env python
"""Development server with multi-app switching."""

import os
import sys
import warnings
from typing import Any, Literal, cast

import rich.traceback
from flask.cli import load_dotenv
from werkzeug import run_simple

from coaster.utils import getbool


def rq_background_worker(*args: Any, **kwargs: Any) -> Any:
    """Import, create and start a new RQ worker in the background process."""
    from funnel import rq  # pylint: disable=import-outside-toplevel

    return rq.get_worker().work(*args, **kwargs)


if __name__ == '__main__':
    rich.traceback.install(show_locals=True, width=None)
    load_dotenv()
    script_dir = os.path.dirname(__file__)
    if script_dir != '.' and not script_dir.endswith('/.'):
        # If this script is not running from the current working directory, add it's
        # path to the Python path so imports work
        sys.path.insert(0, script_dir)
    os.environ['FLASK_ENV'] = 'development'  # Needed for coaster.app.init_app
    os.environ.setdefault('FLASK_DEBUG', '1')
    debug_mode = os.environ['FLASK_DEBUG'].lower() not in {'0', 'false', 'no'}
    ssl_context: str | Literal['adhoc'] | tuple[str, str] | None  # noqa: PYI051
    ssl_context = os.environ.get('FLASK_DEVSERVER_HTTPS')
    if ssl_context is not None:
        if not ssl_context:
            ssl_context = None  # Recast empty string as None
        elif ssl_context == 'adhoc':
            # For type checkers to narrow to a literal value
            ssl_context = cast(Literal['adhoc'], ssl_context)
        elif ':' in ssl_context:
            ssl_context = cast(tuple[str, str], tuple(ssl_context.split(':', 1)))
        else:
            warnings.warn(
                f"FLASK_DEVSERVER_HTTPS env var has invalid value {ssl_context!r}",
                stacklevel=1,
            )
            ssl_context = None

    from funnel.devtest import BackgroundWorker, RichDebuggedApplication, devtest_app

    # Set debug mode on apps
    devtest_app.debug = debug_mode

    background_rq = None
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # Only start RQ worker within the reloader environment
        background_rq = BackgroundWorker(
            rq_background_worker,
            mock_transports=bool(getbool(os.environ.get('MOCK_TRANSPORTS', 'Y'))),
        )
        background_rq.start()

    if debug_mode:
        run_app: Any = RichDebuggedApplication(
            devtest_app, evalex=True, console_path='/_console'
        )
    else:
        run_app = devtest_app

    run_simple(
        os.environ.get('FLASK_RUN_HOST', '127.0.0.1'),
        int(os.environ.get('FLASK_RUN_PORT', '3000')),
        run_app,
        use_reloader=True,
        use_debugger=False,  # Since we've already wrapped the app in the debugger
        threaded=True,
        ssl_context=ssl_context,
        extra_files=['funnel/static/build/manifest.json'],
    )

    if background_rq:
        background_rq.stop()
