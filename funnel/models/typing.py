"""Union types for models with shared functionality."""

from typing import Union

from .account import Account, AccountOldId, Team
from .auth_client import AuthClient
from .comment import Comment, Commentset
from .label import Label
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

__all__ = ['UuidModelUnion', 'SearchModelUnion', 'MarkdownModelUnion']

# All models with a `uuid` attr
UuidModelUnion = Union[
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

# All models with a `search_vector` attr
SearchModelUnion = Union[Account, Comment, Label, Project, Proposal, Session, Update]

# All models with one or more markdown composite columns
MarkdownModelUnion = Union[
    Account, Comment, Project, Proposal, Session, Update, Venue, VenueRoom
]
