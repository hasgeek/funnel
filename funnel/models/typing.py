"""Union types for models with shared functionality."""

from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Literal,
    Protocol,
    TypeAlias,
    Union,
    overload,
    runtime_checkable,
)
from uuid import UUID

from sqlalchemy import Table
from sqlalchemy.orm import Mapped, declared_attr

from coaster.sqlalchemy import LazyRoleSet, QueryProperty
from coaster.utils import InspectableSet

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


class ModelTimestampProtocol(ModelProtocol, Protocol):
    created_at: declared_attr[datetime]
    updated_at: declared_attr[datetime]


class ModelUrlProtocol(Protocol):
    @property
    def absolute_url(self) -> str | None:
        ...

    def url_for(self, action: str = 'view', **kwargs) -> str:
        ...


class ModelRoleProtocol(Protocol):
    def roles_for(
        self, actor: Account | None = None, anchors: Sequence[Any] = ()
    ) -> LazyRoleSet:
        ...

    @property
    def current_roles(self) -> InspectableSet[LazyRoleSet]:
        ...

    @overload
    def actors_with(
        self, roles: Iterable[str], with_role: Literal[False] = False
    ) -> Iterator[Account]:
        ...

    @overload
    def actors_with(
        self, roles: Iterable[str], with_role: Literal[True]
    ) -> Iterator[tuple[Account, str]]:
        ...

    def actors_with(
        self, roles: Iterable[str], with_role: bool = False
    ) -> Iterator[Account | tuple[Account, str]]:
        ...


class ModelIdProtocol(
    ModelTimestampProtocol, ModelUrlProtocol, ModelRoleProtocol, Protocol
):
    id_: declared_attr[Any]


@runtime_checkable  # FIXME: This is never used, but needed to make type checkers happy
class ModelUuidProtocol(ModelIdProtocol, Protocol):
    uuid: declared_attr[UUID]


class ModelSearchProtocol(ModelUuidProtocol, Protocol):
    search_vector: Mapped[str]

    @property
    def title(self) -> Mapped[str] | declared_attr[str]:
        ...
