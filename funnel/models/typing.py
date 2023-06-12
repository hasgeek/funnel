"""Union types for models with shared functionality."""

from typing import Union

from .auth_client import AuthClient
from .comment import Comment, Commentset
from .label import Label
from .membership_mixin import ImmutableMembershipMixin
from .moderation import CommentModeratorReport
from .profile import Profile
from .project import Project
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .sync_ticket import TicketParticipant
from .update import Update
from .user import Organization, Team, User, UserOldId
from .user_session import UserSession
from .venue import Venue, VenueRoom

__all__ = ['UuidModelUnion', 'SearchModelUnion', 'MarkdownModelUnion']

# All models with a `uuid` attr
UuidModelUnion = Union[
    AuthClient,
    Comment,
    CommentModeratorReport,
    Commentset,
    ImmutableMembershipMixin,
    Organization,
    Profile,
    Project,
    Proposal,
    Rsvp,
    Session,
    Team,
    TicketParticipant,
    Update,
    User,
    UserOldId,
    UserSession,
    Venue,
    VenueRoom,
]

# All models with a `search_vector` attr
SearchModelUnion = Union[
    Comment, Label, Organization, Profile, Project, Proposal, Session, Update, User
]

# All models with one or more markdown composite columns
MarkdownModelUnion = Union[
    Comment, Profile, Project, Proposal, Session, Update, Venue, VenueRoom
]
