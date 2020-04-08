# -*- coding: utf-8 -*-

import os.path
import sys

__all__ = ['application']

sys.path.insert(0, os.path.dirname(__file__))
from funnel import lastuserapp as application  # isort:skip
