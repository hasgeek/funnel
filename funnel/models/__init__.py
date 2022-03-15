from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy_utils import LocaleType, TimezoneType, TSVectorType, UUIDType

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

if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property

# This must be set _before_ any of the models are imported
TimestampMixin.__with_timezone__ = True

# Some of these imports are order sensitive due to circular dependencies
# All of them have to be imported after TimestampMixin is patched

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
