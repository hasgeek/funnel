#! /usr/bin/env python

import sys

from funnel import funnelapp

try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    port = 3001
funnelapp.run('0.0.0.0', port=port, debug=True)
