"""Provide configuration for models and import all into a common `models` namespace."""
# flake8: noqa

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeVar

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import LocaleType, TimezoneType, TSVectorType, UUIDType
import sqlalchemy as sa  # noqa
import sqlalchemy.orm  # Required to make sa.orm work  # noqa

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

from ..typing import Mapped

if not TYPE_CHECKING:
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlalchemy.orm import declarative_mixin, declared_attr
else:
    from sqlalchemy.ext.declarative import declared_attr

    hybrid_property = property
    try:
        # sqlalchemy-stubs (by Dropbox) can't find declarative_mixin, but
        # sqlalchemy2-stubs (by SQLAlchemy) requires it
        from sqlalchemy.orm import declarative_mixin  # type: ignore[attr-defined]
    except ImportError:
        T = TypeVar('T')

        def declarative_mixin(cls: T) -> T:
            return cls


db = SQLAlchemy()
# This must be set _before_ any of the models are imported
TimestampMixin.__with_timezone__ = True

# Some of these imports are order sensitive due to circular dependencies
# All of them have to be imported after TimestampMixin is patched

# pylint: disable=wrong-import-position
from .helpers import *  # isort:skip
from .user import *  # isort:skip
from .user_signals import *  # isort:skip
from .user_session import *  # isort:skip
from .email_address import *  # isort:skip
from .auth_client import *  # isort:skip
from .notification import *  # isort:skip
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
from .notification_types import *  # isort:skip
from .commentset_membership import *  # isort:skip
from .geoname import *  # isort:skip
