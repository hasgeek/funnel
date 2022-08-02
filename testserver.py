#!/usr/bin/env python
"""Test server with multi-app switching, only for use from within tests."""

import os
import sys

from werkzeug import run_simple

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(__file__))
    os.environ['FLASK_ENV'] = 'testing'

    from funnel import devtest_app

    run_simple(
        os.environ.get('FLASK_RUN_HOST', '127.0.0.1'),
        int(os.environ.get('FLASK_RUN_PORT', 3002)),
        devtest_app,
        use_reloader=False,
        use_debugger=False,
        use_evalex=False,
        threaded=True,
    )
