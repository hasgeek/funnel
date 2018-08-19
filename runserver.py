#! /usr/bin/env python

import sys
from funnel import app

try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    port = 3000
app.run('0.0.0.0', port=port, debug=True)
