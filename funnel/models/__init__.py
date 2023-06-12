"""Provide configuration for models and import all into a common `models` namespace."""
# flake8: noqa
# pylint: disable=unused-import

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, declared_attr
from sqlalchemy_utils import LocaleType, TimezoneType, TSVectorType
import sqlalchemy as sa

from coaster.sqlalchemy import (
    BaseIdNameMixin,
    BaseMixin,
    BaseNameMixin,
    BaseScopedIdNameMixin,
    BaseScopedNameMixin,
    CoordinatesMixin,
    DynamicMapped,
    ModelBase,
    NoIdMixin,
    Query,
    RegistryMixin,
    RoleMixin,
    TimestampMixin,
    UrlType,
    UuidMixin,
    relationship,
    with_roles,
)
from coaster.sqlalchemy.model import QueryProperty


class Model(ModelBase, DeclarativeBase):
    """Base for all models."""

    __with_timezone__ = True


class GeonameModel(ModelBase, DeclarativeBase):
    """Base for geoname models."""

    __bind_key__ = 'geoname'
    __with_timezone__ = True


# This must be set _before_ any of the models using db.Model are imported
TimestampMixin.__with_timezone__ = True

db = SQLAlchemy(query_class=Query, metadata=Model.metadata)  # type: ignore[arg-type]
Model.init_flask_sqlalchemy(db)
GeonameModel.init_flask_sqlalchemy(db)

# Some of these imports are order sensitive due to circular dependencies
# All of them have to be imported after TimestampMixin is patched

# pylint: disable=wrong-import-position
from . import types  # isort:skip
from .helpers import *  # isort:skip
from .user import *  # isort:skip
from .user_signals import *  # isort:skip
from .user_session import *  # isort:skip
from .email_address import *  # isort:skip
from .phone_number import *  # isort:skip
from .auth_client import *  # isort:skip
from .utils import *  # isort:skip
from .comment import *  # isort:skip
from .draft import *  # isort:skip
from .sync_ticket import *  # isort:skip
from .contact_exchange import *  # isort:skip
from .label import *  # isort:skip
from .profile import *  # isort:skip
from .project import *  # isort:skip
from .update import *  # isort:skip
from .proposal import *  # isort:skip
from .rsvp import *  # isort:skip
from .saved import *  # isort:skip
from .session import *  # isort:skip
from .shortlink import *  # isort:skip
from .venue import *  # isort:skip
from .video_mixin import *  # isort:skip
from .membership_mixin import *  # isort:skip
from .organization_membership import *  # isort:skip
from .project_membership import *  # isort:skip
from .sponsor_membership import *  # isort:skip
from .proposal_membership import *  # isort:skip
from .site_membership import *  # isort:skip
from .moderation import *  # isort:skip
from .commentset_membership import *  # isort:skip
from .geoname import *  # isort:skip
from .typing import *  # isort:skip
from .notification import *  # isort:skip
from .notification_types import *  # isort:skip
