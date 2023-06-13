#!/usr/bin/env python
"""Development server with multi-app switching."""

import os
import sys

from flask.cli import load_dotenv
from werkzeug import run_simple

from coaster.utils import getbool

if __name__ == '__main__':
    load_dotenv()
    sys.path.insert(0, os.path.dirname(__file__))
    os.environ['FLASK_ENV'] = 'development'  # Needed for coaster.app.init_app
    os.environ.setdefault('FLASK_DEBUG', '1')
    debug_mode = os.environ['FLASK_DEBUG'].lower() not in {'0', 'false', 'no'}

    from funnel import rq
    from funnel.devtest import BackgroundWorker, devtest_app

    # Set debug mode on apps
    devtest_app.debug = debug_mode

    background_rq = None
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # Only start RQ worker within the reloader environment
        background_rq = BackgroundWorker(
            rq.get_worker().work,
            mock_transports=bool(getbool(os.environ.get('MOCK_TRANSPORTS', True))),
        )
        background_rq.start()

    run_simple(
        os.environ.get('FLASK_RUN_HOST', '127.0.0.1'),
        int(os.environ.get('FLASK_RUN_PORT', 3000)),
        devtest_app,
        use_reloader=True,
        use_debugger=debug_mode,
        use_evalex=debug_mode,
        threaded=True,
        extra_files=['funnel/static/build/manifest.json'],
    )

    if background_rq:
        background_rq.stop()
