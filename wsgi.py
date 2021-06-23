import os.path
import sys

__all__ = ['application', 'shortlinkapp']

sys.path.insert(0, os.path.dirname(__file__))
from funnel import app as application  # isort:skip
from funnel import shortlinkapp  # isort:skip
