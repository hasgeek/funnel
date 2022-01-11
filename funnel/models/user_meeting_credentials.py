from __future__ import annotations

from typing import Iterable, List, Optional, Set, Union

from sqlalchemy.sql import expression

from baseframe import __
from coaster.sqlalchemy import Query, StateManager, immutable, with_roles
from coaster.utils import LabeledEnum
from datetime import datetime

from ..typing import OptionalMigratedTables
from . import (
    BaseMixin,
    BaseScopedNameMixin,
    MarkdownColumn,
    TSVectorType,
    UrlType,
    UuidMixin,
    db,
    hybrid_property,
)
from .helpers import (
    RESERVED_NAMES,
    ImgeeType,
    add_search_trigger,
    markdown_content_options,
    valid_username,
    visual_field_delimiter,
)
from .user import Organization, User
from .utils import do_migrate_instances

__all__ = ['UserMeetingCredentials']

class UserMeetingCredentials(db.Model, UuidMixin):
    __tablename__ = 'user_meeting_credentials'

    id=db.Column(db.Integer, primary_key = True)
    access_key = db.Column(db.String(100), nullable=True)
    secret_key = db.Column(db.String(100), nullable=True)
    user_id = db.Column(
        None, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True
    )
    provider = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=True, default=False)
    is_deleted = db.Column(db.Boolean, nullable=True, default=False)
    is_default = db.Column(db.Boolean, nullable=True, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        """Represent :class:`Profile` as a string."""
        return f'<UserMeetingCredentials "{self.id}">' 