#! /usr/bin/env python

import sys

from funnel import lastuserapp

try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    port = 7000
lastuserapp.run('0.0.0.0', port=port, debug=True)  # nosec
