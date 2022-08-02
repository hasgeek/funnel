#!/usr/bin/env python
"""Development server with multi-app switching."""

import os
import sys

from werkzeug import run_simple

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(__file__))
    os.environ['FLASK_ENV'] = 'development'

    from funnel import devtest_app

    run_simple(
        os.environ.get('FLASK_RUN_HOST', '127.0.0.1'),
        int(os.environ.get('FLASK_RUN_PORT', 3000)),
        devtest_app,
        use_reloader=True,
        use_debugger=True,
        use_evalex=True,
        threaded=True,
    )
