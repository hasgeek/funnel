#! /usr/bin/env python

import eventlet  # isort:skip

eventlet.monkey_patch()

import sys

from funnel import app, socketio

try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    port = 3002
socketio.run(app, '0.0.0.0', port=port, debug=True)
