# -*- coding: utf-8 -*-
# flake8: noqa

from sqlalchemy_utils import TSVectorType

from coaster.db import db
from coaster.sqlalchemy import (
    BaseIdNameMixin,
    BaseMixin,
    BaseNameMixin,
    BaseScopedIdNameMixin,
    BaseScopedNameMixin,
    CoordinatesMixin,
    JsonDict,
    MarkdownColumn,
    NoIdMixin,
    RoleMixin,
    TimestampMixin,
    UrlType,
    UuidMixin,
    with_roles,
)

TimestampMixin.__with_timezone__ = True

# Some of these imports are order sensitive due to circular dependencies
# All of them have to be imported after TimestampMixin is patched

from .commentvote import *  # isort:skip
from .draft import *  # isort:skip
from .event import *  # isort:skip
from .contact_exchange import *  # isort:skip
from .feedback import *  # isort:skip
from .label import *  # isort:skip
from .profile import *  # isort:skip
from .project import *  # isort:skip
from .proposal import *  # isort:skip
from .rsvp import *  # isort:skip
from .saved import *  # isort:skip
from .session import *  # isort:skip
from .user import *  # isort:skip
from .venue import *  # isort:skip
from .membership import *  # isort:skip