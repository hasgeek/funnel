"""Union types for models with shared functionality."""

from datetime import datetime
from typing import Any, ClassVar, Protocol, TypeAlias, Union
from uuid import UUID

from sqlalchemy import Table
from sqlalchemy.orm import Mapped, declared_attr

from coaster.sqlalchemy import QueryProperty

from .account import Account, AccountOldId, Team
from .auth_client import AuthClient
from .comment import Comment, Commentset
from .login_session import LoginSession
from .membership_mixin import ImmutableMembershipMixin
from .moderation import CommentModeratorReport
from .project import Project
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .sync_ticket import TicketParticipant
from .update import Update
from .venue import Venue, VenueRoom

__all__ = [
    'UuidModelUnion',
    'MarkdownModelUnion',
    'ModelIdProtocol',
    'ModelUuidProtocol',
    'ModelSearchProtocol',
]

# All models with a `uuid` attr
UuidModelUnion: TypeAlias = Union[
    Account,
    AccountOldId,
    AuthClient,
    Comment,
    CommentModeratorReport,
    Commentset,
    ImmutableMembershipMixin,
    LoginSession,
    Project,
    Proposal,
    Rsvp,
    Session,
    Team,
    TicketParticipant,
    Update,
    Venue,
    VenueRoom,
]


# All models with one or more markdown composite columns
MarkdownModelUnion: TypeAlias = Union[
    Account, Comment, Project, Proposal, Session, Update, Venue, VenueRoom
]


class ModelProtocol(Protocol):
    __tablename__: str
    __table__: ClassVar[Table]
    query: ClassVar[QueryProperty]


class ModelIdProtocol(ModelProtocol, Protocol):
    id_: declared_attr[Any]


class ModelTimestampProtocol(ModelProtocol, Protocol):
    created_at: declared_attr[datetime]
    updated_at: declared_attr[datetime]


class ModelUuidProtocol(ModelIdProtocol, Protocol):
    uuid: declared_attr[UUID]


class ModelSearchProtocol(ModelUuidProtocol, ModelTimestampProtocol, Protocol):
    search_vector: Mapped[str]

    @property
    def title(self) -> Mapped[str] | declared_attr[str]:
        ...
