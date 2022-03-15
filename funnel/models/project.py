from __future__ import annotations

from typing import Iterable, List, Optional, Set

from sqlalchemy.orm.collections import attribute_mapped_collection

from flask import current_app
from werkzeug.utils import cached_property

from pytz import utc

from baseframe import __, localize_timezone
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum, buid, utcnow

from ..typing import OptionalMigratedTables
from . import (
    BaseScopedNameMixin,
    JsonDict,
    MarkdownColumn,
    TimestampMixin,
    TimezoneType,
    TSVectorType,
    UrlType,
    UuidMixin,
    db,
)
from .comment import SET_TYPE, Commentset
from .helpers import (
    RESERVED_NAMES,
    ImgeeType,
    add_search_trigger,
    markdown_content_options,
    reopen,
    valid_name,
    visual_field_delimiter,
)
from .profile import Profile
from .user import User

__all__ = ['Project', 'ProjectLocation', 'ProjectRedirect']


# --- Constants ---------------------------------------------------------------


class PROJECT_STATE(LabeledEnum):
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    WITHDRAWN = (2, 'withdrawn', __("Withdrawn"))
    DELETED = (3, 'deleted', __("Deleted"))
    DELETABLE = {DRAFT, PUBLISHED, WITHDRAWN}
    PUBLISHABLE = {DRAFT, WITHDRAWN}


class CFP_STATE(LabeledEnum):
    NONE = (0, 'none', __("None"))
    PUBLIC = (1, 'public', __("Public"))
    CLOSED = (2, 'closed', __("Closed"))
    ANY = {NONE, PUBLIC, CLOSED}


# --- Models ------------------------------------------------------------------


class Project(UuidMixin, BaseScopedNameMixin, db.Model):
    __tablename__ = 'project'
    reserved_names = RESERVED_NAMES

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        User,
        primaryjoin=user_id == User.id,
        backref=db.backref('projects', cascade='all'),
    )
    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False)
    profile = with_roles(
        db.relationship(
            'Profile', backref=db.backref('projects', cascade='all', lazy='dynamic')
        ),
        read={'all'},
        # If profile grants an 'admin' role, make it 'profile_admin' here
        grants_via={None: {'admin': 'profile_admin'}},
        # `profile` only appears in the 'primary' dataset. It must not be included in
        # 'related' or 'without_parent' as it is the parent
        datasets={'primary'},
    )
    parent = db.synonym('profile')
    tagline = with_roles(
        db.Column(db.Unicode(250), nullable=False),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )
    description = with_roles(
        MarkdownColumn(
            'description', default='', nullable=False, options=markdown_content_options
        ),
        read={'all'},
    )
    instructions = with_roles(
        MarkdownColumn(
            'instructions', default='', nullable=True, options=markdown_content_options
        ),
        read={'all'},
    )

    location = with_roles(
        db.Column(db.Unicode(50), default='', nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )
    parsed_location = db.Column(JsonDict, nullable=False, server_default='{}')

    website = with_roles(
        db.Column(UrlType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )
    timezone = with_roles(
        db.Column(TimezoneType(backend='pytz'), nullable=False, default=utc),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', PROJECT_STATE),
        default=PROJECT_STATE.DRAFT,
        nullable=False,
        index=True,
    )
    state = with_roles(
        StateManager('_state', PROJECT_STATE, doc="Project state"), call={'all'}
    )
    _cfp_state = db.Column(
        'cfp_state',
        db.Integer,
        StateManager.check_constraint('cfp_state', CFP_STATE),
        default=CFP_STATE.NONE,
        nullable=False,
        index=True,
    )
    cfp_state = with_roles(
        StateManager('_cfp_state', CFP_STATE, doc="CfP state"), call={'all'}
    )

    #: Audit timestamp to detect re-publishing to re-surface a project
    first_published_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    #: Timestamp of when this project was most recently published
    published_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'all'},
        write={'promoter'},
        datasets={'primary', 'without_parent', 'related'},
    )
    #: Optional start time for schedule, cached from column property schedule_start_at
    start_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'all'},
        write={'editor'},
        datasets={'primary', 'without_parent', 'related'},
    )
    #: Optional end time for schedule, cached from column property schedule_end_at
    end_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True),
        read={'all'},
        write={'editor'},
        datasets={'primary', 'without_parent', 'related'},
    )

    cfp_start_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    cfp_end_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)

    bg_image = with_roles(
        db.Column(ImgeeType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent', 'related'},
    )
    allow_rsvp = db.Column(db.Boolean, default=False, nullable=False)
    buy_tickets_url = db.Column(UrlType, nullable=True)

    banner_video_url = with_roles(
        db.Column(UrlType, nullable=True),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )
    boxoffice_data = with_roles(
        db.Column(JsonDict, nullable=False, server_default='{}'),
        # This is an attribute, but we deliberately use `call` instead of `read` to
        # block this from dictionary enumeration. FIXME: Break up this dictionary into
        # individual columns with `all` access for ticket embed id and `promoter`
        # access for ticket sync access token.
        call={'all'},
    )

    hasjob_embed_url = with_roles(db.Column(UrlType, nullable=True), read={'all'})
    hasjob_embed_limit = with_roles(db.Column(db.Integer, default=8), read={'all'})

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(
        Commentset,
        uselist=False,
        cascade='all',
        single_parent=True,
        back_populates='project',
    )

    parent_id = db.Column(
        None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True
    )
    parent_project = db.relationship(
        'Project', remote_side='Project.id', backref='subprojects'
    )

    #: Featured project flag. This can only be set by website editors, not
    #: project editors or profile admins.
    site_featured = with_roles(
        db.Column(db.Boolean, default=False, nullable=False),
        read={'all'},
        write={'site_editor'},
        datasets={'primary', 'without_parent'},
    )

    #: Version number maintained by SQLAlchemy, used for vCal files, starting at 1
    versionid = with_roles(db.Column(db.Integer, nullable=False), read={'all'})

    search_vector = db.deferred(
        db.Column(
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
                hltext=lambda: db.func.concat_ws(
                    visual_field_delimiter,
                    Project.title,
                    Project.location,
                    Project.description_html,
                    Project.instructions_html,
                ),
            ),
            nullable=False,
        )
    )

    livestream_urls = with_roles(
        db.Column(db.ARRAY(db.UnicodeText, dimensions=1), server_default='{}'),
        read={'all'},
        datasets={'primary', 'without_parent'},
    )

    __table_args__ = (
        db.UniqueConstraint('profile_id', 'name'),
        db.Index('ix_project_search_vector', 'search_vector', postgresql_using='gin'),
        db.CheckConstraint(
            db.or_(
                db.and_(start_at.is_(None), end_at.is_(None)),
                db.and_(start_at.isnot(None), end_at.isnot(None), end_at > start_at),
            ),
            'project_start_at_end_at_check',
        ),
        db.CheckConstraint(
            db.or_(
                db.and_(cfp_start_at.is_(None), cfp_end_at.is_(None)),
                db.and_(cfp_start_at.isnot(None), cfp_end_at.is_(None)),
                db.and_(
                    cfp_start_at.isnot(None),
                    cfp_end_at.isnot(None),
                    cfp_end_at > cfp_start_at,
                ),
            ),
            'project_cfp_start_at_cfp_end_at_check',
        ),
    )

    __mapper_args__ = {'version_id_col': versionid}

    __roles__ = {
        'all': {
            'read': {
                'absolute_url',  # From UrlForMixin
                'name',  # From BaseScopedNameMixin
                'short_title',  # From BaseScopedNameMixin
                'title',  # From BaseScopedNameMixin
                'urls',  # From UrlForMixin
                'created_at',  # From TimestampMixin, used for ical render timestamp
                'updated_at',  # From TimestampMixin, used for ical render timestamp
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
        lambda project: db.func.utcnow() >= project.end_at,
        label=('past', __("Past")),
    )
    state.add_conditional_state(
        'LIVE',
        state.PUBLISHED,
        lambda project: (
            project.start_at is not None
            and project.start_at <= utcnow() < project.end_at
        ),
        lambda project: db.and_(
            project.start_at <= db.func.utcnow(),
            db.func.utcnow() < project.end_at,
        ),
        label=('live', __("Live")),
    )
    state.add_conditional_state(
        'UPCOMING',
        state.PUBLISHED,
        lambda project: project.start_at is not None and utcnow() < project.start_at,
        lambda project: db.func.utcnow() < project.start_at,
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
        lambda project: db.and_(
            project.instructions_html.isnot(None), project.instructions_html != ''
        ),
        label=('draft', __("Draft")),
    )
    cfp_state.add_conditional_state(
        'OPEN',
        cfp_state.PUBLIC,
        lambda project: project.cfp_end_at is None or (utcnow() < project.cfp_end_at),
        lambda project: db.or_(
            project.cfp_end_at.is_(None), db.func.utcnow() < project.cfp_end_at
        ),
        label=('open', __("Open")),
    )
    cfp_state.add_conditional_state(
        'EXPIRED',
        cfp_state.PUBLIC,
        lambda project: project.cfp_end_at is not None
        and utcnow() >= project.cfp_end_at,
        lambda project: db.and_(
            project.cfp_end_at.isnot(None), db.func.utcnow() >= project.cfp_end_at
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
        new_membership = ProjectCrewMembership(
            parent=self,
            user=self.user,
            granted_by=self.user,
            is_editor=True,
            is_promoter=True,
        )
        db.session.add(new_membership)

    def __repr__(self):
        """Represent :class:`Project` as a string."""
        return '<Project {}/{} "{}">'.format(
            self.profile.name if self.profile else '(none)',
            self.name,
            self.title,
        )

    @with_roles(call={'editor'})
    @cfp_state.transition(
        cfp_state.OPENABLE,
        cfp_state.PUBLIC,
        title=__("Enable submissions"),
        message=__("Submissions will be accepted until the optional closing date"),
        type='success',
    )
    def open_cfp(self):
        # If closing date is in the past, remove it
        if self.cfp_end_at is not None and self.cfp_end_at <= utcnow():
            self.cfp_end_at = None
        # If opening date is not set, set it
        if self.cfp_start_at is None:
            self.cfp_start_at = db.func.utcnow()

    @with_roles(call={'editor'})
    @cfp_state.transition(
        cfp_state.PUBLIC,
        cfp_state.CLOSED,
        title=__("Disable submissions"),
        message=__("Submissions will no longer be accepted"),
        type='success',
    )
    def close_cfp(self):
        pass

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
            self.first_published_at = db.func.utcnow()
            first_published = True
        self.published_at = db.func.utcnow()
        return first_published

    @with_roles(call={'editor'})
    @state.transition(
        state.PUBLISHED,
        state.WITHDRAWN,
        title=__("Withdraw project"),
        message=__("The project has been withdrawn and is no longer listed"),
        type='success',
    )
    def withdraw(self):
        pass

    @property
    def title_inline(self) -> str:
        """Suffix a colon if the title does not end in ASCII sentence punctuation."""
        if self.title and self.tagline:
            if not self.title[-1] in ('?', '!', ':', ';', '.', ','):
                return self.title + ':'
        return self.title

    with_roles(title_inline, read={'all'}, datasets={'primary', 'without_parent'})

    @property
    def title_suffix(self) -> str:
        """
        Return the profile's title if the project's title doesn't derive from it.

        Used in HTML title tags to render <title>{{ project }} - {{ suffix }}</title>.
        """
        if not self.title.startswith(self.parent.title):
            return self.profile.title
        return ''

    with_roles(title_suffix, read={'all'})

    @with_roles(call={'all'})
    def joined_title(self, sep: str = '›') -> str:
        """Return the project's title joined with the profile's title, if divergent."""
        if self.short_title == self.title:
            # Project title does not derive from profile title, so use both
            return f"{self.profile.title} {sep} {self.title}"
        # Project title extends profile title, so profile title is not needed
        return self.title

    @property
    def full_title(self) -> str:
        """Return :meth:`joined_title` as a property."""
        return self.joined_title()

    with_roles(
        full_title, read={'all'}, datasets={'primary', 'without_parent', 'related'}
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
        daterange = ''
        if self.start_at is not None and self.end_at is not None:
            schedule_start_at_date = self.start_at_localized.date()
            schedule_end_at_date = self.end_at_localized.date()
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
            daterange = daterange_format.format(
                start_date=schedule_start_at_date.strftime(strf_date),
                end_date=schedule_end_at_date.strftime('%d %b'),
                year=schedule_end_at_date.year,
            )
        return ', '.join([_f for _f in [daterange, self.location] if _f])

    # TODO: Removing Delete feature till we figure out siteadmin feature
    # @with_roles(call={'editor'})
    # @state.transition(
    #     state.DELETABLE, state.DELETED, title=__("Delete project"),
    #     message=__("The project has been deleted"), type='success')
    # def delete(self):
    #     pass

    @db.validates('name', 'profile')
    def _validate_and_create_redirect(self, key, value):
        # TODO: When labels, venues and other resources are relocated from project to
        # profile, this validator can no longer watch profile change. We'll need a more
        # elaborate transfer mechanism that remaps resources to equivalent ones in the
        # new profile.
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

    def update_schedule_timestamps(self):
        """Update cached timestamps from sessions."""
        self.start_at = self.schedule_start_at
        self.end_at = self.schedule_end_at

    def roles_for(self, actor: Optional[User], anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        # https://github.com/hasgeek/funnel/pull/220#discussion_r168718052
        roles.add('reader')
        return roles

    def is_safe_to_delete(self) -> bool:
        """Return True if project has no proposals."""
        return self.proposals.count() == 0

    @classmethod
    def order_by_date(cls):
        """
        Return an order by clause for the project's start_at or published_at.

        param bool desc: Use descending order (default True)
        """
        clause = db.case(
            [(cls.start_at.isnot(None), cls.start_at)],
            else_=cls.published_at,
        )
        return clause

    @classmethod
    def all_unsorted(cls):
        """Return query of all published projects, without ordering criteria."""
        return cls.query.outerjoin(Venue).filter(cls.state.PUBLISHED)

    @classmethod
    def all(cls):
        """Return all published projects, ordered by date."""
        return cls.all_unsorted().order_by(cls.order_by_date())

    @classmethod
    def fetch_sorted(cls):
        return cls.query.filter(cls.state.PUBLISHED).order_by(cls.order_by_date())

    # The base class offers `get(parent, name)`. We accept f'{parent}/{name}' here for
    # convenience as this is only used in shell access.
    @classmethod
    def get(cls, profile_project):  # skipcq: PYL-W0221
        """Get a project by its URL slug in the form ``<profile>/<project>``."""
        profile_name, project_name = profile_project.split('/')
        return (
            cls.query.join(Profile)
            .filter(Profile.name == profile_name, Project.name == project_name)
            .one_or_none()
        )

    @classmethod
    def migrate_profile(
        cls, old_profile: Profile, new_profile: Profile
    ) -> OptionalMigratedTables:
        names = {project.name for project in new_profile.projects}
        for project in old_profile.projects:
            if project.name in names:
                current_app.logger.warning(
                    "Project %r had a conflicting name in profile migration,"
                    " so renaming by adding adding random value to name",
                    project,
                )
                project.name += '-' + buid()
            project.profile = new_profile
        return None


add_search_trigger(Project, 'search_vector')


@reopen(Profile)
class __Profile:
    id: db.Column

    listed_projects = db.relationship(
        Project,
        lazy='dynamic',
        primaryjoin=db.and_(
            Profile.id == Project.profile_id,
            Project.state.PUBLISHED,
        ),
        viewonly=True,
    )
    draft_projects = db.relationship(
        Project,
        lazy='dynamic',
        primaryjoin=db.and_(
            Profile.id == Project.profile_id,
            db.or_(Project.state.DRAFT, Project.cfp_state.DRAFT),
        ),
        viewonly=True,
    )
    projects_by_name = with_roles(
        db.relationship(
            Project, collection_class=attribute_mapped_collection('name'), viewonly=True
        ),
        read={'all'},
    )

    def draft_projects_for(self, user: Optional[User]) -> List[Project]:
        if user is not None:
            return [
                membership.project
                for membership in user.projects_as_crew_active_memberships.join(
                    Project, Profile
                ).filter(
                    # Project is attached to this profile
                    Project.profile_id == self.id,
                    # Project is in draft state OR has a draft call for proposals
                    db.or_(Project.state.DRAFT, Project.cfp_state.DRAFT),
                )
            ]
        return []

    def unscheduled_projects_for(self, user: Optional[User]) -> List[Project]:
        if user is not None:
            return [
                membership.project
                for membership in user.projects_as_crew_active_memberships.join(
                    Project, Profile
                ).filter(
                    # Project is attached to this profile
                    Project.profile_id == self.id,
                    # Project is in draft state OR has a draft call for proposals
                    db.or_(Project.state.PUBLISHED_WITHOUT_SESSIONS),
                )
            ]
        return []


class ProjectRedirect(TimestampMixin, db.Model):
    __tablename__ = 'project_redirect'

    profile_id = db.Column(
        None, db.ForeignKey('profile.id'), nullable=False, primary_key=True
    )
    profile = db.relationship(
        'Profile', backref=db.backref('project_redirects', cascade='all')
    )
    parent = db.synonym('profile')
    name = db.Column(db.Unicode(250), nullable=False, primary_key=True)

    project_id = db.Column(
        None, db.ForeignKey('project.id', ondelete='SET NULL'), nullable=True
    )
    project = db.relationship(Project, backref='redirects')

    def __repr__(self):
        """Represent :class:`ProjectRedirect` as a string."""
        return '<ProjectRedirect {}/{}: {}>'.format(
            self.profile.name,
            self.name,
            self.project.name if self.project else '(none)',
        )

    def redirect_view_args(self):
        if self.project:
            return {'profile': self.profile.name, 'project': self.project.name}
        else:
            return {}

    @classmethod
    def add(cls, project, profile=None, name=None):
        """
        Add a project redirect in a given profile.

        :param project: The project to create a redirect for
        :param profile: The profile to place the redirect in, defaulting to existing
        :param str name: Name to redirect, defaulting to project's existing name

        Typical use is when a project is renamed, to create a redirect from its previous
        name, or when it's moved between projects, to create a redirect from previous
        project.
        """
        if profile is None:
            profile = project.profile
        if name is None:
            name = project.name
        redirect = ProjectRedirect.query.get((profile.id, name))
        if redirect is None:
            redirect = ProjectRedirect(profile=profile, name=name, project=project)
            db.session.add(redirect)
        else:
            redirect.project = project
        return redirect

    @classmethod
    def migrate_profile(
        cls, old_profile: Profile, new_profile: Profile
    ) -> OptionalMigratedTables:
        """
        Discard redirects when migrating profiles.

        Since there is no profile redirect, all project redirects will also be
        unreachable and are no longer relevant.
        """
        names = {pr.name for pr in new_profile.project_redirects}
        for pr in old_profile.project_redirects:
            if pr.name not in names:
                pr.profile = new_profile
            else:
                # Discard project redirect since the name is already taken by another
                # redirect in the new profile
                db.session.delete(pr)
        return None


class ProjectLocation(TimestampMixin, db.Model):
    __tablename__ = 'project_location'
    #: Project we are tagging
    project_id = db.Column(
        None, db.ForeignKey('project.id'), primary_key=True, nullable=False
    )
    project = db.relationship(Project, backref=db.backref('locations', cascade='all'))
    #: Geonameid for this project
    geonameid = db.Column(db.Integer, primary_key=True, nullable=False, index=True)
    primary = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        """Represent :class:`ProjectLocation` as a string."""
        return '<ProjectLocation %d %s for project %s>' % (
            self.geonameid,
            'primary' if self.primary else 'secondary',
            self.project,
        )


@reopen(Commentset)
class __Commentset:
    project = with_roles(
        db.relationship(Project, uselist=False, back_populates='commentset'),
        grants_via={None: {'editor': 'document_subscriber'}},
    )


# Tail imports
from .project_membership import ProjectCrewMembership  # isort:skip  # skipcq: FLK-E402
from .venue import Venue  # isort:skip  # skipcq: FLK-E402
