import sys
import os.path

__all__ = ['application']

sys.path.insert(0, os.path.dirname(__file__))
from funnel import app as application  # isort:skip
