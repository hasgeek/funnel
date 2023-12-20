"""Project model."""
# pylint: disable=unnecessary-lambda

from __future__ import annotations

from collections import OrderedDict, defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, Self, cast, overload

from flask_babel import format_date, get_locale
from furl import furl
from isoweek import Week
from pytz import BaseTzInfo, utc
from sqlalchemy.ext.orderinglist import OrderingList, ordering_list
from werkzeug.utils import cached_property

from baseframe import __, localize_timezone
from coaster.sqlalchemy import (
    DynamicAssociationProxy,
    LazyRoleSet,
    StateManager,
    with_roles,
)
from coaster.utils import LabeledEnum, buid, utcnow

from .. import app
from . import (
    BaseScopedNameMixin,
    DynamicMapped,
    Mapped,
    Model,
    Query,
    TimestampMixin,
    TimezoneType,
    TSVectorType,
    UrlType,
    UuidMixin,
    db,
    hybrid_property,
    relationship,
    sa,
    sa_orm,
    types,
)
from .account import Account
from .comment import SET_TYPE, Commentset
from .helpers import (
    RESERVED_NAMES,
    ImgeeType,
    MarkdownCompositeDocument,
    add_search_trigger,
    valid_name,
    visual_field_delimiter,
)

__all__ = ['PROJECT_RSVP_STATE', 'Project', 'ProjectLocation', 'ProjectRedirect']


# --- Constants ---------------------------------------------------------------


class PROJECT_STATE(LabeledEnum):  # noqa: N801
    DRAFT = (1, 'draft', __("Draft"))
    PUBLISHED = (2, 'published', __("Published"))
    WITHDRAWN = (3, 'withdrawn', __("Withdrawn"))
    DELETED = (4, 'deleted', __("Deleted"))
    DELETABLE = {DRAFT, PUBLISHED, WITHDRAWN}
    PUBLISHABLE = {DRAFT, WITHDRAWN}


class CFP_STATE(LabeledEnum):  # noqa: N801
    NONE = (1, 'none', __("None"))
    PUBLIC = (2, 'public', __("Public"))
    CLOSED = (3, 'closed', __("Closed"))
    ANY = {NONE, PUBLIC, CLOSED}


class PROJECT_RSVP_STATE(LabeledEnum):  # noqa: N801
    NONE = (1, __("Not accepting registrations"))
    ALL = (2, __("Anyone can register"))
    MEMBERS = (3, __("Only members can register"))


# --- Models ------------------------------------------------------------------


class Project(UuidMixin, BaseScopedNameMixin, Model):
    __tablename__ = 'project'
    reserved_names = RESERVED_NAMES

    created_by_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False
    )
    created_by: Mapped[Account] = relationship(foreign_keys=[created_by_id])
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False
    )
    account: Mapped[Account] = with_roles(
        relationship(foreign_keys=[account_id], back_populates='projects'),
        read={'all'},
        # If account grants an 'admin' role, make it 'account_admin' here
        grants_via={
            None: {
                'admin': 'account_admin',
                'follower': 'account_participant',
                'member': 'account_member',
            }
        },
        # `account` only appears in the 'primary' dataset. It must not be included in
        # 'related' or 'without_parent' as it is the parent
        datasets={'primary'},
    )
    parent: Mapped[Account] = sa_orm.synonym('account')
    tagline: Mapped[str] = with_roles(
        sa_orm.mapped_column(sa.Unicode(250), nullable=False),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )
    description, description_text, description_html = MarkdownCompositeDocument.create(
        'description', default='', nullable=False
    )
    with_roles(description, read={'all'})
    (
        instructions,
        instructions_text,
        instructions_html,
    ) = MarkdownCompositeDocument.create('instructions', default='', nullable=True)
    with_roles(instructions, read={'all'})

    location: Mapped[str | None] = with_roles(
        sa_orm.mapped_column(sa.Unicode(50), default='', nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )
    parsed_location: Mapped[types.jsonb_dict]

    website: Mapped[furl | None] = with_roles(
        sa_orm.mapped_column(UrlType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )
    timezone: Mapped[BaseTzInfo] = with_roles(
        sa_orm.mapped_column(TimezoneType(backend='pytz'), nullable=False, default=utc),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )

    _state: Mapped[int] = sa_orm.mapped_column(
        'state',
        sa.Integer,
        StateManager.check_constraint('state', PROJECT_STATE),
        default=PROJECT_STATE.DRAFT,
        nullable=False,
        index=True,
    )
    state = with_roles(
        StateManager['Project']('_state', PROJECT_STATE, doc="Project state"),
        call={'all'},
    )
    _cfp_state: Mapped[int] = sa_orm.mapped_column(
        'cfp_state',
        sa.Integer,
        StateManager.check_constraint('cfp_state', CFP_STATE),
        default=CFP_STATE.NONE,
        nullable=False,
        index=True,
    )
    cfp_state = with_roles(
        StateManager['Project']('_cfp_state', CFP_STATE, doc="CfP state"), call={'all'}
    )

    #: State of RSVPs
    rsvp_state: Mapped[int] = with_roles(
        sa_orm.mapped_column(
            sa.SmallInteger,
            StateManager.check_constraint('rsvp_state', PROJECT_RSVP_STATE),
            default=PROJECT_RSVP_STATE.NONE,
            nullable=False,
        ),
        read={'all'},
        write={'editor', 'promoter'},
        datasets={'primary', 'without_parent', 'related'},
    )

    #: Audit timestamp to detect re-publishing to re-surface a project
    first_published_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    #: Timestamp of when this project was most recently published
    published_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'all'},
        write={'promoter'},
        datasets={'primary', 'without_parent', 'related'},
    )
    #: Optional start time for schedule, cached from column property schedule_start_at
    start_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'all'},
        write={'editor'},
        datasets={'primary', 'without_parent', 'related'},
    )
    #: Optional end time for schedule, cached from column property schedule_end_at
    end_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'all'},
        write={'editor'},
        datasets={'primary', 'without_parent', 'related'},
    )

    cfp_start_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True, index=True
    )
    cfp_end_at: Mapped[datetime | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True, index=True
    )

    bg_image: Mapped[furl | None] = with_roles(
        sa_orm.mapped_column(ImgeeType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )

    #: Auto-generated preview image for Open Graph
    preview_image: Mapped[bytes | None] = sa_orm.mapped_column(
        sa.LargeBinary, nullable=True, deferred=True
    )

    buy_tickets_url: Mapped[furl | None] = with_roles(
        sa_orm.mapped_column(UrlType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )

    banner_video_url: Mapped[furl | None] = with_roles(
        sa_orm.mapped_column(UrlType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )
    boxoffice_data: Mapped[types.jsonb_dict] = with_roles(
        sa_orm.mapped_column(),
        # This is an attribute, but we deliberately use `call` instead of `read` to
        # block this from dictionary enumeration. FIXME: Break up this dictionary into
        # individual columns with `all` access for ticket embed id and `promoter`
        # access for ticket sync access token.
        call={'all'},
    )

    hasjob_embed_url: Mapped[furl | None] = with_roles(
        sa_orm.mapped_column(UrlType, nullable=True), read={'all'}
    )
    hasjob_embed_limit: Mapped[int | None] = with_roles(
        sa_orm.mapped_column(sa.Integer, default=8, nullable=True), read={'all'}
    )

    commentset_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('commentset.id'), nullable=False
    )
    commentset: Mapped[Commentset] = relationship(
        uselist=False, single_parent=True, back_populates='project'
    )

    parent_project_id: Mapped[int | None] = sa_orm.mapped_column(
        'parent_id',  # TODO: Migration required
        sa.ForeignKey('project.id', ondelete='SET NULL'),
        nullable=True,
    )
    parent_project: Mapped[Project | None] = relationship(
        remote_side='Project.id', back_populates='subprojects'
    )
    subprojects: Mapped[list[Project]] = relationship(back_populates='parent_project')

    #: Featured project flag. This can only be set by website editors, not
    #: project editors or account admins.
    site_featured: Mapped[bool] = with_roles(
        sa_orm.mapped_column(sa.Boolean, default=False, nullable=False),
        read={'all'},
        write={'site_editor'},
        datasets={'primary', 'without_parent'},
    )

    livestream_urls: Mapped[list[str] | None] = with_roles(
        sa_orm.mapped_column(
            sa.ARRAY(sa.UnicodeText, dimensions=1),
            nullable=True,  # For legacy data
            server_default=sa.text("'{}'::text[]"),
        ),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )

    is_restricted_video: Mapped[bool] = with_roles(
        sa_orm.mapped_column(sa.Boolean, default=False, nullable=False),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )

    #: Revision number maintained by SQLAlchemy, used for vCal files, starting at 1
    revisionid: Mapped[int] = with_roles(
        sa_orm.mapped_column(sa.Integer, nullable=False), read={'all'}
    )

    search_vector: Mapped[str] = sa_orm.mapped_column(
        TSVectorType(
            'name',
            'title',
            'description_text',
            'instructions_text',
            'location',
            weights={
                'name': 'A',
                'title': 'A',
                'description_text': 'B',
                'instructions_text': 'B',
                'location': 'C',
            },
            regconfig='english',
            hltext=lambda: sa.func.concat_ws(
                visual_field_delimiter,
                Project.title,
                Project.location,
                Project.description_html,
                Project.instructions_html,
            ),
        ),
        nullable=False,
        deferred=True,
    )

    # --- Backrefs and relationships

    redirects: Mapped[list[ProjectRedirect]] = relationship(back_populates='project')
    locations: Mapped[list[ProjectLocation]] = relationship(back_populates='project')

    # label.py
    labels: Mapped[list[Label]] = relationship(
        primaryjoin=lambda: sa.and_(
            Label.project_id == Project.id,
            Label.main_label_id.is_(None),
            Label._archived.is_(False),  # pylint: disable=protected-access
        ),
        order_by=lambda: Label.seq,
        viewonly=True,
    )
    all_labels: Mapped[OrderingList[Label]] = relationship(
        collection_class=ordering_list('seq', count_from=1),
        back_populates='project',
    )

    # project_membership.py
    crew_memberships: DynamicMapped[ProjectMembership] = relationship(
        lazy='dynamic', passive_deletes=True, back_populates='project'
    )
    active_crew_memberships: DynamicMapped[ProjectMembership] = with_roles(
        relationship(
            lazy='dynamic',
            primaryjoin=lambda: sa.and_(
                ProjectMembership.project_id == Project.id,
                ProjectMembership.is_active,
            ),
            viewonly=True,
        ),
        grants_via={'member': {'editor', 'promoter', 'usher', 'participant', 'crew'}},
    )

    active_editor_memberships: DynamicMapped[ProjectMembership] = relationship(
        lazy='dynamic',
        primaryjoin=lambda: sa.and_(
            ProjectMembership.project_id == Project.id,
            ProjectMembership.is_active,
            ProjectMembership.is_editor.is_(True),
        ),
        viewonly=True,
    )

    active_promoter_memberships: DynamicMapped[ProjectMembership] = relationship(
        lazy='dynamic',
        primaryjoin=lambda: sa.and_(
            ProjectMembership.project_id == Project.id,
            ProjectMembership.is_active,
            ProjectMembership.is_promoter.is_(True),
        ),
        viewonly=True,
    )

    active_usher_memberships: DynamicMapped[ProjectMembership] = relationship(
        lazy='dynamic',
        primaryjoin=lambda: sa.and_(
            ProjectMembership.project_id == Project.id,
            ProjectMembership.is_active,
            ProjectMembership.is_usher.is_(True),
        ),
        viewonly=True,
    )

    crew = DynamicAssociationProxy[Account]('active_crew_memberships', 'member')
    editors = DynamicAssociationProxy[Account]('active_editor_memberships', 'member')
    promoters = DynamicAssociationProxy[Account](
        'active_promoter_memberships', 'member'
    )
    ushers = DynamicAssociationProxy[Account]('active_usher_memberships', 'member')

    # proposal.py
    proposals: DynamicMapped[Proposal] = relationship(
        lazy='dynamic', order_by=lambda: Proposal.seq, back_populates='project'
    )

    # rsvp.py
    rsvps: DynamicMapped[Rsvp] = relationship(lazy='dynamic', back_populates='project')

    # saved.py
    saves: DynamicMapped[SavedProject] = relationship(
        lazy='dynamic', passive_deletes=True, back_populates='project'
    )

    # session.py
    sessions: DynamicMapped[Session] = relationship(
        lazy='dynamic', back_populates='project'
    )

    if TYPE_CHECKING:
        # These are column properties, defined at the end of the file
        schedule_start_at: Mapped[datetime | None]
        next_session_at: Mapped[datetime | None]
        schedule_end_at: Mapped[datetime | None]
        # This relationship is added by add_primary_relationship in models/venue.py
        primary_venue: Mapped[Venue | None] = relationship()

    # sponsor_membership.py
    all_sponsor_memberships: DynamicMapped[ProjectSponsorMembership] = relationship(
        lazy='dynamic', passive_deletes=True, back_populates='project'
    )

    sponsor_memberships: DynamicMapped[ProjectSponsorMembership] = with_roles(
        relationship(
            lazy='dynamic',
            primaryjoin=lambda: sa.and_(
                ProjectSponsorMembership.project_id == Project.id,
                ProjectSponsorMembership.is_active,
            ),
            order_by=lambda: ProjectSponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self) -> bool:
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy[Account]('sponsor_memberships', 'member')

    # sync_ticket.py
    ticket_clients: Mapped[list[TicketClient]] = relationship(back_populates='project')
    ticket_events: Mapped[list[TicketEvent]] = relationship(back_populates='project')
    ticket_types: Mapped[list[TicketType]] = relationship(back_populates='project')
    # XXX: This relationship exposes an edge case in RoleMixin. It previously expected
    # TicketParticipant.participant to be unique per project, meaning one user could
    # have one participant ticket only. This is not guaranteed by the model as tickets
    # are unique per email address per ticket type, and one user can have (a) two email
    # addresses with tickets, or (b) tickets of different types. RoleMixin has since
    # been patched to look for the first matching record (.first() instead of .one()).
    # This may expose a new edge case in future in case the TicketParticipant model adds
    # an `offered_roles` method, as only the first matching record's method will be
    # called
    ticket_participants: DynamicMapped[TicketParticipant] = with_roles(
        relationship(lazy='dynamic', back_populates='project'),
        grants_via={
            'participant': {'participant', 'project_participant', 'ticket_participant'}
        },
    )

    # update.py
    updates: DynamicMapped[Update] = relationship(
        lazy='dynamic', back_populates='project'
    )

    # venue.py
    venues: Mapped[OrderingList[Venue]] = with_roles(
        relationship(
            order_by=lambda: Venue.seq,
            collection_class=ordering_list('seq', count_from=1),
            back_populates='project',
        ),
        read={'all'},
    )

    @property
    def rooms(self):
        return [room for venue in self.venues for room in venue.rooms]

    __table_args__ = (
        sa.UniqueConstraint('account_id', 'name'),
        sa.Index('ix_project_search_vector', 'search_vector', postgresql_using='gin'),
        sa.CheckConstraint(
            sa.or_(
                sa.and_(start_at.is_(None), end_at.is_(None)),
                sa.and_(start_at.is_not(None), end_at.is_not(None), end_at > start_at),
            ),
            'project_start_at_end_at_check',
        ),
        sa.CheckConstraint(
            sa.or_(
                sa.and_(cfp_start_at.is_(None), cfp_end_at.is_(None)),
                sa.and_(cfp_start_at.is_not(None), cfp_end_at.is_(None)),
                sa.and_(
                    cfp_start_at.is_not(None),
                    cfp_end_at.is_not(None),
                    cfp_end_at > cfp_start_at,
                ),
            ),
            'project_cfp_start_at_cfp_end_at_check',
        ),
    )

    __mapper_args__ = {'version_id_col': revisionid}

    __roles__ = {
        'all': {
            'read': {
                'absolute_url',  # From UrlForMixin
                'name',  # From BaseScopedNameMixin
                'short_title',  # From BaseScopedNameMixin
                'title',  # From BaseScopedNameMixin
                'urls',  # From UrlForMixin
                'created_at',  # From TimestampMixin, used for vCal render timestamp
                'updated_at',  # From TimestampMixin, used for vCal render timestamp
            },
            'call': {
                'features',  # From RegistryMixin
                'forms',  # From RegistryMixin
                'url_for',  # From UrlForMixin
                'view_for',  # From UrlForMixin
                'views',  # From RegistryMixin
            },
        },
    }

    __datasets__ = {
        'primary': {
            'absolute_url',  # From UrlForMixin
            'name',  # From BaseScopedNameMixin
            'title',  # From BaseScopedNameMixin
            'urls',  # From UrlForMixin
        },
        'without_parent': {
            'absolute_url',  # From UrlForMixin
            'name',  # From BaseScopedNameMixin
            'title',  # From BaseScopedNameMixin
        },
        'related': {
            'absolute_url',  # From UrlForMixin
            'name',  # From BaseScopedNameMixin
            'title',  # From BaseScopedNameMixin
        },
    }

    state.add_conditional_state(
        'PAST',
        state.PUBLISHED,
        lambda project: project.end_at is not None and utcnow() >= project.end_at,
        lambda project: sa.func.utcnow() >= project.end_at,
        label=('past', __("Past")),
    )
    state.add_conditional_state(
        'LIVE',
        state.PUBLISHED,
        lambda project: (
            project.start_at is not None
            and project.end_at is not None
            and project.start_at <= utcnow() < project.end_at
        ),
        lambda project: sa.and_(
            project.start_at <= sa.func.utcnow(),
            sa.func.utcnow() < project.end_at,
        ),
        label=('live', __("Live")),
    )
    state.add_conditional_state(
        'UPCOMING',
        state.PUBLISHED,
        lambda project: project.start_at is not None and utcnow() < project.start_at,
        lambda project: sa.func.utcnow() < project.start_at,
        label=('upcoming', __("Upcoming")),
    )
    state.add_conditional_state(
        'PUBLISHED_WITHOUT_SESSIONS',
        state.PUBLISHED,
        lambda project: project.start_at is None,
        lambda project: project.start_at.is_(None),
        label=('published_without_sessions', __("Published without sessions")),
    )

    cfp_state.add_conditional_state(
        'HAS_PROPOSALS',
        cfp_state.ANY,
        lambda project: db.session.query(project.proposals.exists()).scalar(),
        label=('has_proposals', __("Has submissions")),
    )
    cfp_state.add_conditional_state(
        'HAS_SESSIONS',
        cfp_state.ANY,
        lambda project: db.session.query(project.sessions.exists()).scalar(),
        label=('has_sessions', __("Has sessions")),
    )
    cfp_state.add_conditional_state(
        'DRAFT',
        cfp_state.NONE,
        lambda project: project.instructions_html != '',
        lambda project: sa.and_(
            project.instructions_html.is_not(None), project.instructions_html != ''
        ),
        label=('draft', __("Draft")),
    )
    cfp_state.add_conditional_state(
        'OPEN',
        cfp_state.PUBLIC,
        lambda project: project.cfp_end_at is None or (utcnow() < project.cfp_end_at),
        lambda project: sa.or_(
            project.cfp_end_at.is_(None), sa.func.utcnow() < project.cfp_end_at
        ),
        label=('open', __("Open")),
    )
    cfp_state.add_conditional_state(
        'EXPIRED',
        cfp_state.PUBLIC,
        lambda project: project.cfp_end_at is not None
        and utcnow() >= project.cfp_end_at,
        lambda project: sa.and_(
            project.cfp_end_at.is_not(None), sa.func.utcnow() >= project.cfp_end_at
        ),
        label=('expired', __("Expired")),
    )

    cfp_state.add_state_group(
        'OPENABLE',
        cfp_state.CLOSED,
        cfp_state.NONE,
        cfp_state.EXPIRED,
    )
    cfp_state.add_state_group(
        'UNAVAILABLE',
        cfp_state.CLOSED,
        cfp_state.EXPIRED,
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.commentset = Commentset(settype=SET_TYPE.PROJECT)
        # Add the creator as editor and promoter
        new_membership = ProjectMembership(
            parent=self,
            member=self.created_by,
            granted_by=self.created_by,
            is_editor=True,
            is_promoter=True,
        )
        db.session.add(new_membership)

    def __repr__(self) -> str:
        """Represent :class:`Project` as a string."""
        return f'<Project {self.account.urlname}/{self.name} "{self.title}">'

    def __str__(self) -> str:
        return self.joined_title

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return self.joined_title
        return format(self.joined_title, format_spec)

    @with_roles(call={'editor'})
    @cfp_state.transition(
        cfp_state.OPENABLE,
        cfp_state.PUBLIC,
        title=__("Enable submissions"),
        message=__("Submissions will be accepted until the optional closing date"),
        type='success',
    )
    def open_cfp(self) -> None:
        """Change state to accept submissions."""
        # If closing date is in the past, remove it
        if self.cfp_end_at is not None and self.cfp_end_at <= utcnow():
            self.cfp_end_at = None
        # If opening date is not set, set it
        if self.cfp_start_at is None:
            self.cfp_start_at = sa.func.utcnow()

    @with_roles(call={'editor'})  # skipcq: PTC-W0049
    @cfp_state.transition(
        cfp_state.PUBLIC,
        cfp_state.CLOSED,
        title=__("Disable submissions"),
        message=__("Submissions will no longer be accepted"),
        type='success',
    )
    def close_cfp(self) -> None:
        """Change state to not accept submissions."""

    @with_roles(call={'editor'})
    @state.transition(
        state.PUBLISHABLE,
        state.PUBLISHED,
        title=__("Publish project"),
        message=__("The project has been published"),
        type='success',
    )
    def publish(self) -> bool:
        """Publish a project and return a flag if this is the first publishing."""
        first_published = False
        if not self.first_published_at:
            self.first_published_at = sa.func.utcnow()
            first_published = True
        self.published_at = sa.func.utcnow()
        return first_published

    @with_roles(call={'editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.PUBLISHED,
        state.WITHDRAWN,
        title=__("Withdraw project"),
        message=__("The project has been withdrawn and is no longer listed"),
        type='success',
    )
    def withdraw(self):
        """Withdraw a project."""

    @property
    def title_inline(self) -> str:
        """Suffix a colon if the title does not end in ASCII sentence punctuation."""
        if self.title and self.tagline:
            # pylint: disable=unsubscriptable-object
            if self.title[-1] not in ('?', '!', ':', ';', '.', ','):
                return self.title + ':'
        return self.title

    with_roles(title_inline, read={'all'}, datasets={'primary', 'without_parent'})

    @property
    def title_suffix(self) -> str:
        """
        Return the account's title if the project's title doesn't derive from it.

        Used in HTML title tags to render <title>{{ project }} - {{ suffix }}</title>.
        """
        if not self.title.startswith(self.account.title):
            return self.account.title
        return ''

    with_roles(title_suffix, read={'all'})

    @property
    def title_parts(self) -> list[str]:
        """
        Return the hierarchy of titles of this project.

        If the project's title is an extension of the account's title, only the
        project's title is returned as a single list item. If they are distinct, both
        are returned.

        This list is used by :prop:`joined_title` to produce a slash-separated title,
        but can be used directly when another rendering is required.
        """
        if self.short_title == self.title:
            # Project title does not derive from account title, so use both
            return [self.account.title, self.title]
        # Project title extends account title, so account title is not needed
        return [self.title]

    with_roles(title_parts, read={'all'})

    @property
    def joined_title(self) -> str:
        """Return the project's title joined with the account's title, if divergent."""
        return ' / '.join(self.title_parts)

    with_roles(
        joined_title, read={'all'}, datasets={'primary', 'without_parent', 'related'}
    )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent', 'related'})
    @cached_property
    def datelocation(self) -> str:
        """
        Return a date and location string for the project.

        The format depends on project dates:

        1. If it's a single day event:
            > 11 Feb 2018, Bangalore

        2. If multi-day event in same month:
            > 09–12 Feb 2018, Bangalore

        3. If multi-day event across months:
            > 27 Feb–02 Mar 2018, Bangalore

        4. If multi-day event across years:
            > 30 Dec 2018–02 Jan 2019, Bangalore
        """
        # FIXME: Replace strftime with Babel formatting
        start_at = self.start_at_localized
        end_at = self.end_at_localized
        if start_at is not None and end_at is not None:
            schedule_start_at_date = start_at.date()
            schedule_end_at_date = end_at.date()
            daterange_format = '{start_date}–{end_date} {year}'
            if schedule_start_at_date == schedule_end_at_date:
                # if both dates are same, in case of single day project
                strf_date = ''
                daterange_format = '{end_date} {year}'
            elif schedule_start_at_date.year != schedule_end_at_date.year:
                # if the start date and end dates are in different years,
                strf_date = '%d %b %Y'
            elif schedule_start_at_date.month != schedule_end_at_date.month:
                # If multi-day event across months
                strf_date = '%d %b'
            elif schedule_start_at_date.month == schedule_end_at_date.month:
                # If multi-day event in same month
                strf_date = '%d'
            else:
                raise ValueError(
                    "This should not happen: unknown date range"
                    f" {schedule_start_at_date}–{schedule_end_at_date}"
                )
            daterange = daterange_format.format(
                start_date=schedule_start_at_date.strftime(strf_date),
                end_date=schedule_end_at_date.strftime('%d %b'),
                year=schedule_end_at_date.year,
            )
        else:
            daterange = ''
        return ', '.join([_f for _f in [daterange, self.location] if _f])

    # TODO: Removing Delete feature till we figure out siteadmin feature
    # @with_roles(call={'editor'})
    # @state.transition(
    #     state.DELETABLE, state.DELETED, title=__("Delete project"),
    #     message=__("The project has been deleted"), type='success')
    # def delete(self):
    #     pass

    @sa_orm.validates('name', 'account')
    def _validate_and_create_redirect(self, key: str, value: str | None) -> str:
        # TODO: When labels, venues and other resources are relocated from project to
        # account, this validator can no longer watch for `account` change. We'll need a
        # more elaborate transfer mechanism that remaps resources to equivalent ones in
        # the new `account`.
        if key == 'name':
            value = value.strip() if value is not None else None
        if not value or (key == 'name' and not valid_name(value)):
            raise ValueError(f"Invalid value for {key}: {value!r}")
        existing_value = getattr(self, key)
        if value != existing_value and existing_value is not None:
            ProjectRedirect.add(self)
        return value

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def cfp_start_at_localized(self):
        return (
            localize_timezone(self.cfp_start_at, tz=self.timezone)
            if self.cfp_start_at
            else None
        )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def cfp_end_at_localized(self):
        return (
            localize_timezone(self.cfp_end_at, tz=self.timezone)
            if self.cfp_end_at
            else None
        )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def start_at_localized(self):
        """Return localized start_at timestamp."""
        return (
            localize_timezone(self.start_at, tz=self.timezone)
            if self.start_at
            else None
        )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def end_at_localized(self):
        """Return localized end_at timestamp."""
        return localize_timezone(self.end_at, tz=self.timezone) if self.end_at else None

    @with_roles(read={'all'}, datasets={'primary', 'without_parent', 'related'})
    @hybrid_property
    def allow_rsvp(self) -> bool:
        """RSVP state as a boolean value (allowed for all or not)."""
        return self.rsvp_state == PROJECT_RSVP_STATE.ALL

    @property
    def active_rsvps(self) -> Query[Rsvp]:
        return self.rsvps.join(Account).filter(Rsvp.state.YES, Account.state.ACTIVE)

    @overload
    def rsvp_for(self, account: Account, create: Literal[True]) -> Rsvp:
        ...

    @overload
    def rsvp_for(self, account: Account | None, create: Literal[False]) -> Rsvp | None:
        ...

    def rsvp_for(self, account: Account | None, create=False) -> Rsvp | None:
        return Rsvp.get_for(cast(Project, self), account, create)

    def rsvps_with(self, status: str):
        return (
            cast(Project, self)
            .rsvps.join(Account)
            .filter(
                Account.state.ACTIVE,
                Rsvp._state == status,  # pylint: disable=protected-access
            )
        )

    def rsvp_counts(self) -> dict[str, int]:
        return {
            row[0]: row[1]
            for row in db.session.query(
                Rsvp._state,  # pylint: disable=protected-access
                sa.func.count(Rsvp._state),  # pylint: disable=protected-access
            )
            .join(Account)
            .filter(Account.state.ACTIVE, Rsvp.project == self)
            .group_by(Rsvp._state)  # pylint: disable=protected-access
            .all()
        }

    @cached_property
    def rsvp_count_going(self) -> int:
        return (
            cast(Project, self)
            .rsvps.join(Account)
            .filter(Account.state.ACTIVE, Rsvp.state.YES)
            .count()
        )

    def update_schedule_timestamps(self) -> None:
        """Update cached timestamps from sessions."""
        self.start_at = self.schedule_start_at
        self.end_at = self.schedule_end_at

    def roles_for(
        self, actor: Account | None = None, anchors: Sequence = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        # https://github.com/hasgeek/funnel/pull/220#discussion_r168718052
        roles.add('reader')
        return roles

    def is_safe_to_delete(self) -> bool:
        """Return True if project has no proposals."""
        return self.proposals.count() == 0

    @property
    def proposals_all(self):
        if self.subprojects:
            return Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        return self.proposals

    @property
    def proposals_by_state(self):
        if self.subprojects:
            basequery = Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            basequery = Proposal.query.filter_by(project=self)
        return Proposal.state.group(
            basequery.filter(
                ~(Proposal.state.DRAFT), ~(Proposal.state.DELETED)
            ).order_by(sa.desc('created_at'))
        )

    @property
    def proposals_by_confirmation(self):
        if self.subprojects:
            basequery = Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            basequery = Proposal.query.filter_by(project=self)
        return {
            'confirmed': basequery.filter(Proposal.state.CONFIRMED)
            .order_by(sa.desc('created_at'))
            .all(),
            'unconfirmed': basequery.filter(
                ~(Proposal.state.CONFIRMED),
                ~(Proposal.state.DRAFT),
                ~(Proposal.state.DELETED),
            )
            .order_by(sa.desc('created_at'))
            .all(),
        }

    if TYPE_CHECKING:
        _has_featured_proposals: Mapped[bool | None]

    @property
    def has_featured_proposals(self) -> bool:
        return bool(self._has_featured_proposals)

    with_roles(has_featured_proposals, read={'all'})

    @with_roles(call={'all'})
    def is_saved_by(self, account: Account) -> bool:
        return account is not None and self.saves.filter_by(account=account).notempty()

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def schedule_start_at_localized(self) -> datetime | None:
        return (
            localize_timezone(self.schedule_start_at, tz=self.timezone)
            if self.schedule_start_at
            else None
        )

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def schedule_end_at_localized(self) -> datetime | None:
        return (
            localize_timezone(self.schedule_end_at, tz=self.timezone)
            if self.schedule_end_at
            else None
        )

    @with_roles(read={'all'})
    @cached_property
    def session_count(self) -> int:
        return self.sessions.filter(Session.start_at.is_not(None)).count()

    featured_sessions: Mapped[list[Session]] = with_roles(
        relationship(
            order_by=lambda: Session.start_at.asc(),
            primaryjoin=lambda: sa.and_(
                Session.project_id == Project.id, Session.featured.is_(True)
            ),
            viewonly=True,
        ),
        read={'all'},
    )
    scheduled_sessions: Mapped[list[Session]] = with_roles(
        relationship(
            order_by=lambda: Session.start_at.asc(),
            primaryjoin=lambda: sa.and_(
                Session.project_id == Project.id,
                Session.scheduled,
            ),
            viewonly=True,
        ),
        read={'all'},
    )
    unscheduled_sessions: Mapped[list[Session]] = with_roles(
        relationship(
            order_by=lambda: Session.start_at.asc(),
            primaryjoin=lambda: sa.and_(
                Session.project_id == Project.id,
                Session.scheduled.is_not(True),
            ),
            viewonly=True,
        ),
        read={'all'},
    )

    sessions_with_video: DynamicMapped[Session] = with_roles(
        relationship(
            lazy='dynamic',
            primaryjoin=lambda: sa.and_(
                Project.id == Session.project_id,
                Session.video_id.is_not(None),
                Session.video_source.is_not(None),
            ),
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sessions_with_video(self) -> bool:
        return self.query.session.query(self.sessions_with_video.exists()).scalar()

    def next_session_from(self, timestamp: datetime) -> Session | None:
        """Find the next session in this project from given timestamp."""
        return (
            self.sessions.filter(
                Session.start_at.is_not(None), Session.start_at >= timestamp
            )
            .order_by(Session.start_at.asc())
            .first()
        )

    @with_roles(call={'all'})
    def next_starting_at(self, timestamp: datetime | None = None) -> datetime | None:
        """
        Return timestamp of next session from given timestamp.

        Supplements :attr:`next_session_at` to also consider projects without sessions.
        """
        # If there's no `self.start_at`, there is no session either
        if self.start_at is not None:
            if timestamp is None:
                timestamp = utcnow()
            # If `self.start_at` is in the future, it is guaranteed to be the closest
            # timestamp, so return it directly
            if self.start_at >= timestamp:
                return self.start_at
            # In the past? Then look for a session and return that timestamp, if any
            return (
                db.session.query(sa.func.min(Session.start_at))
                .filter(
                    Session.start_at.is_not(None),
                    Session.start_at >= timestamp,
                    Session.project == self,
                )
                .scalar()
            )

        return None

    @classmethod
    def starting_at(
        cls, timestamp: datetime, within: timedelta, gap: timedelta
    ) -> Query[Self]:
        """
        Return projects that are about to start, for sending notifications.

        :param datetime timestamp: The timestamp to look for new sessions at
        :param timedelta within: Find anything at timestamp + within delta. Lookup will
            be for sessions where timestamp >= start_at < timestamp+within
        :param timedelta gap: A project will be considered to be starting if it has no
            sessions ending within the gap period before the timestamp

        Typical use of this method is from a background worker that calls it at
        intervals of five minutes with parameters (timestamp, within 5m, 60m gap).
        """
        # As a rule, start_at is queried with >= and <, end_at with > and <= because
        # they represent inclusive lower and upper bounds.

        # Check project starting time before looking for individual sessions, as some
        # projects will have no sessions
        return (
            cls.query.filter(
                cls.id.in_(
                    db.session.query(sa.func.distinct(Session.project_id)).filter(
                        Session.start_at.is_not(None),
                        Session.start_at >= timestamp,
                        Session.start_at < timestamp + within,
                        Session.project_id.notin_(
                            db.session.query(
                                sa.func.distinct(Session.project_id)
                            ).filter(
                                Session.start_at.is_not(None),
                                sa.or_(
                                    sa.and_(
                                        Session.start_at >= timestamp - gap,
                                        Session.start_at < timestamp,
                                    ),
                                    sa.and_(
                                        Session.end_at > timestamp - gap,
                                        Session.end_at <= timestamp,
                                    ),
                                ),
                            )
                        ),
                    )
                )
            )
            .join(Session.project)
            .filter(cls.state.PUBLISHED)
        ).union(
            cls.query.filter(
                cls.state.PUBLISHED,
                cls.start_at.is_not(None),
                cls.start_at >= timestamp,
                cls.start_at < timestamp + within,
            )
        )

    @with_roles(call={'all'})
    def current_sessions(self) -> dict | None:
        if self.start_at is None or (self.start_at > utcnow() + timedelta(minutes=30)):
            return None

        current_sessions = (
            self.sessions.outerjoin(VenueRoom)
            .filter(Session.start_at <= sa.func.utcnow() + timedelta(minutes=30))
            .filter(Session.end_at > sa.func.utcnow())
            .order_by(Session.start_at.asc(), VenueRoom.seq.asc())
        )

        return {
            'sessions': [
                session.current_access(datasets=('without_parent', 'related'))
                for session in current_sessions
            ],
            'rooms': [
                room.current_access(datasets=('without_parent', 'related'))
                for room in self.rooms
            ],
        }

    # TODO: Use TypedDict for return type
    def calendar_weeks(self, leading_weeks: bool = True) -> dict[str, Any]:
        # session_dates is a list of tuples in this format -
        # (date, day_start_at, day_end_at, event_count)
        if self.schedule_start_at:
            session_dates = list(
                db.session.query(
                    sa.func.date_trunc(
                        'day', sa.func.timezone(self.timezone.zone, Session.start_at)
                    ).label('date'),
                    sa.func.min(Session.start_at).label('day_start_at'),
                    sa.func.max(Session.end_at).label('day_end_at'),
                    sa.func.count().label('count'),
                )
                .select_from(Session)
                .filter(
                    Session.project == self,
                    Session.start_at.is_not(None),
                    Session.end_at.is_not(None),
                )
                .group_by('date')
                .order_by('date')
            )
        elif self.start_at:
            start_at = cast(datetime, self.start_at_localized)
            end_at = cast(datetime, self.end_at_localized)
            if start_at.date() == end_at.date():
                session_dates = [(start_at, start_at, end_at, 1)]
            else:
                session_dates = [
                    (
                        start_at + timedelta(days=plusdays),
                        start_at + timedelta(days=plusdays),
                        end_at - timedelta(days=plusdays),
                        1,
                    )
                    for plusdays in range(
                        (
                            end_at.replace(hour=1, minute=0, second=0, microsecond=0)
                            - start_at.replace(
                                hour=0, minute=0, second=0, microsecond=0
                            )
                        ).days
                        + 1
                    )
                ]
        else:
            session_dates = []

        session_dates_dict = {
            date.date(): {
                'day_start_at': day_start_at,
                'day_end_at': day_end_at,
                'count': count,
            }
            for date, day_start_at, day_end_at, count in session_dates
        }

        # FIXME: This doesn't work. This code needs to be tested in isolation
        # session_dates = (
        #     db.session.query(
        #         sa.cast(
        #             sa.func.date_trunc(
        #                 'day', sa.func.timezone(self.timezone.zone, Session.start_at)
        #             ),
        #             sa.Date,
        #         ).label('date'),
        #         sa.func.count().label('count'),
        #     )
        #     .filter(Session.project == self, Session.scheduled)
        #     .group_by(sa.text('date'))
        #     .order_by(sa.text('date'))
        # )

        # if the project's week is within next 2 weeks, send current week as well
        now = utcnow().astimezone(self.timezone)
        current_week = Week.withdate(now)

        if leading_weeks and self.schedule_start_at is not None:
            schedule_start_week = Week.withdate(self.schedule_start_at)

            # session_dates is a list of tuples in this format -
            # (date, day_start_at, day_end_at, event_count)
            # as these days dont have any event, day_start/end_at are None,
            # and count is 0.
            if (
                schedule_start_week > current_week
                and (schedule_start_week - current_week) <= 2
            ):
                if (schedule_start_week - current_week) == 2:
                    # add this so that the next week's dates
                    # are also included in the calendar.
                    session_dates.insert(0, (now + timedelta(days=7), None, None, 0))
                session_dates.insert(0, (now, None, None, 0))

        weeks: dict[str, dict[str, Any]] = defaultdict(dict)
        today = now.date()
        for project_date, _day_start_at, _day_end_at, session_count in session_dates:
            weekobj = Week.withdate(project_date)
            weekid = weekobj.isoformat()
            if weekid not in weeks:
                weeks[weekid]['year'] = weekobj.year
                # Order is important, and we need dict to count easily
                weeks[weekid]['dates'] = OrderedDict()
            for wdate in weekobj.days():
                weeks[weekid]['dates'].setdefault(wdate, 0)
                if project_date.date() == wdate:
                    # If the event is over don't set upcoming for current week
                    if wdate >= today and weekobj >= current_week and session_count > 0:
                        weeks[weekid]['upcoming'] = True
                    weeks[weekid]['dates'][wdate] += session_count
                    if 'month' not in weeks[weekid]:
                        weeks[weekid]['month'] = format_date(wdate, 'MMM')
        # Extract sorted weeks as a list
        weeks_list = [v for k, v in sorted(weeks.items())]

        for week in weeks_list:
            # Converting to JSON messes up dictionary key order even though we used
            # OrderedDict. This turns the OrderedDict into a list of tuples and JSON
            # preserves that order.
            week['dates'] = [
                {
                    'isoformat': date.isoformat(),
                    'day': format_date(date, 'd'),
                    'count': count,
                    'day_start_at': (
                        session_dates_dict[date]['day_start_at']
                        .astimezone(self.timezone)
                        .strftime('%I:%M %p')
                        if date in session_dates_dict.keys()
                        else None
                    ),
                    'day_end_at': (
                        session_dates_dict[date]['day_end_at']
                        .astimezone(self.timezone)
                        .strftime('%I:%M %p %Z')
                        if date in session_dates_dict.keys()
                        else None
                    ),
                }
                for date, count in week['dates'].items()
            ]
        return {
            'locale': get_locale(),
            'weeks': weeks_list,
            'today': now.date().isoformat(),
            'days': [format_date(day, 'EEE') for day in Week.thisweek().days()],
        }

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def calendar_weeks_full(self) -> dict[str, Any]:  # TODO: Use TypedDict
        return self.calendar_weeks(leading_weeks=True)

    @with_roles(read={'all'}, datasets={'primary', 'without_parent'})
    @cached_property
    def calendar_weeks_compact(self) -> dict[str, Any]:  # TODO: Use TypedDict
        return self.calendar_weeks(leading_weeks=False)

    @property
    def published_updates(self) -> Query[Update]:
        return self.updates.filter(Update.state.PUBLISHED).order_by(
            Update.is_pinned.desc(), Update.published_at.desc()
        )

    with_roles(published_updates, read={'all'})

    @property
    def draft_updates(self) -> Query[Update]:
        return self.updates.filter(Update.state.DRAFT).order_by(Update.created_at)

    with_roles(draft_updates, read={'editor'})

    @property
    def pinned_update(self) -> Update | None:
        return (
            self.updates.filter(Update.state.PUBLISHED, Update.is_pinned.is_(True))
            .order_by(Update.published_at.desc())
            .first()
        )

    with_roles(pinned_update, read={'all'})

    @classmethod
    def order_by_date(cls) -> sa.Case:
        """
        Return an order by clause for the project's start_at or published_at.

        param bool desc: Use descending order (default True)
        """
        clause = sa.case(
            (cls.start_at.is_not(None), cls.start_at),
            else_=cls.published_at,
        )
        return clause

    @classmethod
    def all_unsorted(cls) -> Query[Self]:
        """Return query of all published projects, without ordering criteria."""
        return (
            cls.query.join(Account, Project.account)
            .outerjoin(Venue)
            .filter(cls.state.PUBLISHED, Account.is_verified.is_(True))
        )

    @classmethod
    def all(cls) -> Query[Self]:  # noqa: A003
        """Return all published projects, ordered by date."""
        return cls.all_unsorted().order_by(cls.order_by_date())

    # The base class offers `get(parent, name)`. We accept f'{parent}/{name}' here for
    # convenience as this is only used in shell access.
    @classmethod
    def get(  # type: ignore[override]  # pylint: disable=arguments-differ
        cls, account_project: str
    ) -> Project | None:
        """Get a project by its URL slug in the form ``<account>/<project>``."""
        account_name, project_name = account_project.split('/')
        return (
            cls.query.join(Account, Project.account)
            .filter(Account.name_is(account_name), Project.name == project_name)
            .one_or_none()
        )

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate from one account to another when merging users."""
        names = {project.name for project in new_account.projects}
        for project in old_account.projects:
            if project.name in names:
                app.logger.warning(
                    "Project %r had a conflicting name in account migration,"
                    " so renaming by adding adding random value to name",
                    project,
                )
                project.name += '-' + buid()
            project.account = new_account


add_search_trigger(Project, 'search_vector')


class ProjectRedirect(TimestampMixin, Model):
    __tablename__ = 'project_redirect'

    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False, primary_key=True
    )
    account: Mapped[Account] = relationship(back_populates='project_redirects')
    parent: Mapped[Account] = sa_orm.synonym('account')
    name: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(250), nullable=False, primary_key=True
    )

    project_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id', ondelete='SET NULL'), nullable=True
    )
    project: Mapped[Project | None] = relationship(back_populates='redirects')

    def __repr__(self) -> str:
        """Represent :class:`ProjectRedirect` as a string."""
        if not self.project:
            return f'<ProjectRedirect {self.account.urlname}/{self.name}: (none)>'
        return (
            f'<ProjectRedirect {self.account.urlname}/{self.name}'
            f' → {self.project.account.urlname}/{self.project.name}>'
        )

    def redirect_view_args(self):
        if self.project:
            return {'account': self.account.urlname, 'project': self.project.name}
        return {}

    @classmethod
    def add(
        cls,
        project: Project,
        account: Account | None = None,
        name: str | None = None,
    ) -> ProjectRedirect:
        """
        Add a project redirect in a given account.

        :param project: The project to create a redirect for
        :param account: The account to place the redirect in, defaulting to existing
        :param str name: Name to redirect, defaulting to project's existing name

        Typical use is when a project is renamed, to create a redirect from its previous
        name, or when it's moved between accounts, to create a redirect from previous
        account.
        """
        if account is None:
            account = project.account
        if name is None:
            name = project.name
        redirect = cls.query.get((account.id, name))
        if redirect is None:
            redirect = cls(account=account, name=name, project=project)
            db.session.add(redirect)
        else:
            redirect.project = project
        return redirect

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """
        Transfer project redirects when migrating accounts, discarding dupe names.

        Since there is no account redirect, all project redirects will also be
        unreachable after this transfer, unless the new account is renamed to take the
        old account's name.
        """
        names = {pr.name for pr in new_account.project_redirects}
        for pr in old_account.project_redirects:
            if pr.name not in names:
                pr.account = new_account
            else:
                # Discard project redirect since the name is already taken by another
                # redirect in the new account
                db.session.delete(pr)


class ProjectLocation(TimestampMixin, Model):
    __tablename__ = 'project_location'
    #: Project we are tagging
    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), primary_key=True, nullable=False
    )
    project: Mapped[Project] = relationship(back_populates='locations')
    #: Geonameid for this project
    geonameid: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, primary_key=True, nullable=False, index=True
    )
    primary: Mapped[bool] = sa_orm.mapped_column(
        sa.Boolean, default=True, nullable=False
    )

    def __repr__(self) -> str:
        """Represent :class:`ProjectLocation` as a string."""
        pri_sec = 'primary' if self.primary else 'secondary'
        return (
            f'<ProjectLocation {self.geonameid} {pri_sec} for project {self.project!r}>'
        )


# Tail imports
from .label import Label
from .project_membership import ProjectMembership
from .proposal import Proposal
from .rsvp import Rsvp
from .session import Session
from .sponsor_membership import ProjectSponsorMembership
from .update import Update
from .venue import Venue, VenueRoom

if TYPE_CHECKING:
    from .saved import SavedProject
    from .sync_ticket import TicketClient, TicketEvent, TicketParticipant, TicketType


# Whether the project has any featured proposals. Returns `None` instead of
# a boolean if the project does not have any proposal.
# pylint: disable=protected-access
Project._has_featured_proposals = sa_orm.column_property(
    sa.exists()
    .where(Proposal.project_id == Project.id)
    .where(Proposal.featured.is_(True))
    .correlate_except(Proposal),
    deferred=True,
)
# pylint: enable=protected-access


# Project schedule column expressions. Guide:
# https://docs.sqlalchemy.org/en/13/orm/mapped_sql_expr.html#using-column-property
Project.schedule_start_at = with_roles(
    sa_orm.column_property(
        sa.select(sa.func.min(Session.start_at))
        .where(Session.start_at.is_not(None))
        .where(Session.project_id == Project.id)
        .correlate_except(Session)
        .scalar_subquery()
    ),
    read={'all'},
    datasets={'primary', 'without_parent'},
)

Project.next_session_at = with_roles(
    sa_orm.column_property(
        sa.select(sa.func.min(sa.column('start_at')))
        .select_from(
            sa.select(sa.func.min(Session.start_at).label('start_at'))
            .where(Session.start_at.is_not(None))
            .where(Session.start_at >= sa.func.utcnow())
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
            .union(
                sa.select(Project.start_at.label('start_at'))
                .where(Project.start_at.is_not(None))
                .where(Project.start_at >= sa.func.utcnow())
                .correlate(Project)
            )
            .subquery()
        )
        .scalar_subquery()
    ),
    read={'all'},
)

Project.schedule_end_at = with_roles(
    sa_orm.column_property(
        sa.select(sa.func.max(Session.end_at))
        .where(Session.end_at.is_not(None))
        .where(Session.project_id == Project.id)
        .correlate_except(Session)
        .scalar_subquery()
    ),
    read={'all'},
    datasets={'primary', 'without_parent'},
)

with_roles(
    Project.active_rsvps,
    # This has to use a column reference because 'active_rsvps' has a join on Account
    # and SQLAlchemy will interpret filter_by params to refer to attributes on the last
    # joined model, not the first
    grants_via={Rsvp.participant: {'participant', 'project_participant'}},
)
