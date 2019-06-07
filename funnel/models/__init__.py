# -*- coding: utf-8 -*-
# flake8: noqa

import sqlalchemy.orm
from sqlalchemy_utils import TSVectorType
from sqlalchemy_searchable import make_searchable
from coaster.sqlalchemy import (TimestampMixin, UuidMixin, BaseMixin, BaseNameMixin,
    BaseScopedNameMixin, BaseScopedIdNameMixin, BaseIdNameMixin, MarkdownColumn,
    JsonDict, NoIdMixin, CoordinatesMixin, UrlType)
from coaster.db import db


TimestampMixin.__with_timezone__ = True
make_searchable()


from .commentvote import *
from .contact_exchange import *
from .draft import *
from .event import *
from .feedback import *
from .profile import *
from .project import *
from .proposal import *
from .rsvp import *
from .session import *
from .user import *
from .venue import *
from .label import *


sqlalchemy.orm.configure_mappers()
