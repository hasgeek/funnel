# -*- coding: utf-8 -*-
from funnel import *
from funnel.models import *
import IPython
from urlparse import urlparse


import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

IPython.embed()
