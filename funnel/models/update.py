"""Model for updates to a project."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self

from baseframe import __
from coaster.sqlalchemy import StateManager, auto_init_default, role_check, with_roles
from coaster.utils import LabeledEnum

from .account import Account
from .base import (
    BaseScopedIdNameMixin,
    Mapped,
    Model,
    Query,
    TSVectorType,
    UuidMixin,
    db,
    relationship,
    sa,
    sa_orm,
)
from .comment import SET_TYPE, Commentset
from .helpers import (
    MarkdownCompositeDocument,
    add_search_trigger,
    visual_field_delimiter,
)
from .project import Project

__all__ = ['Update', 'VISIBILITY_STATE']


class UPDATE_STATE(LabeledEnum):  # noqa: N801
    DRAFT = (1, 'draft', __("Draft"))
    PUBLISHED = (2, 'published', __("Published"))
    DELETED = (3, 'deleted', __("Deleted"))


class VISIBILITY_STATE(LabeledEnum):  # noqa: N801
    PUBLIC = (1, 'public', __("Public"))
    PARTICIPANTS = (2, 'participants', __("Participants"))
    MEMBERS = (3, 'members', __("Members"))


class Update(UuidMixin, BaseScopedIdNameMixin[int, Account], Model):
    __tablename__ = 'update'

    # FIXME: Why is this a state? There's no state change in the product design.
    # It's a permanent subtype identifier
    _visibility_state: Mapped[int] = sa_orm.mapped_column(
        'visibility_state',
        sa.SmallInteger,
        StateManager.check_constraint(
            'visibility_state', VISIBILITY_STATE, sa.SmallInteger
        ),
        default=VISIBILITY_STATE.PUBLIC,
        nullable=False,
        index=True,
    )
    visibility_state = StateManager['Update'](
        '_visibility_state', VISIBILITY_STATE, doc="Visibility state"
    )

    _state: Mapped[int] = sa_orm.mapped_column(
        'state',
        sa.SmallInteger,
        StateManager.check_constraint('state', UPDATE_STATE, sa.SmallInteger),
        default=UPDATE_STATE.DRAFT,
        nullable=False,
        index=True,
    )
    state = StateManager['Update']('_state', UPDATE_STATE, doc="Update state")

    created_by_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), default=None, nullable=False, index=True
    )
    created_by: Mapped[Account] = with_roles(
        relationship(
            back_populates='created_updates',
            foreign_keys=[created_by_id],
        ),
        read={'all'},
        grants={'creator'},
    )

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id'), default=None, nullable=False, index=True
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='updates'),
        read={'all'},
        datasets={'primary'},
        grants_via={
            None: {
                'reader': {'project_reader'},  # Project reader is NOT update reader
                'editor': {'editor', 'project_editor'},
                'participant': {'project_participant'},
                'account_follower': {'account_follower'},
                'account_member': {'account_member'},
                'member_participant': {'member_participant'},
                'crew': {'project_crew', 'reader'},
            }
        },
    )
    parent: Mapped[Project] = sa_orm.synonym('project')

    body, body_text, body_html = MarkdownCompositeDocument.create(
        'body', nullable=False
    )

    #: Update serial number, only assigned when the update is published
    number: Mapped[int | None] = with_roles(
        sa_orm.mapped_column(default=None), read={'all'}
    )

    #: Pin an update above future updates
    is_pinned: Mapped[bool] = with_roles(
        sa_orm.mapped_column(default=False), read={'all'}, write={'editor'}
    )

    published_by_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), default=None, nullable=True, index=True
    )
    published_by: Mapped[Account | None] = with_roles(
        relationship(
            back_populates='published_updates',
            foreign_keys=[published_by_id],
        ),
        read={'all'},
    )
    published_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True), read={'all'}
    )

    deleted_by_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), default=None, nullable=True, index=True
    )
    deleted_by: Mapped[Account | None] = with_roles(
        relationship(back_populates='deleted_updates', foreign_keys=[deleted_by_id]),
        read={'reader'},
    )
    deleted_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True),
        read={'reader'},
    )

    edited_at: Mapped[datetime | None] = with_roles(
        sa_orm.mapped_column(sa.TIMESTAMP(timezone=True), nullable=True), read={'all'}
    )

    commentset_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('commentset.id', ondelete='RESTRICT'), nullable=False
    )
    commentset: Mapped[Commentset] = with_roles(
        relationship(
            uselist=False,
            lazy='joined',
            single_parent=True,
            cascade='save-update, merge, delete, delete-orphan',
            back_populates='update',
        ),
        read={'all'},
    )

    search_vector: Mapped[str] = sa_orm.mapped_column(
        TSVectorType(
            'name',
            'title',
            'body_text',
            weights={'name': 'A', 'title': 'A', 'body_text': 'B'},
            regconfig='english',
            # FIXME: Search preview will give partial access to Update.body even if the
            # user does not have the necessary 'reader' role
            hltext=lambda: sa.func.concat_ws(
                visual_field_delimiter, Update.title, Update.body_html
            ),
        ),
        nullable=False,
        deferred=True,
    )

    __roles__ = {
        'all': {
            'read': {'name', 'title', 'urls'},
            'call': {'features', 'visibility_state', 'state', 'url_for'},
        },
        'project_crew': {'read': {'body'}},
        'editor': {'write': {'title', 'body'}, 'read': {'body'}},
        'reader': {'read': {'body'}},
    }

    __datasets__ = {
        'primary': {
            'name',
            'title',
            'number',
            'body',
            'body_text',
            'body_html',
            'published_at',
            'edited_at',
            'created_by',
            'is_pinned',
            'is_currently_restricted',
            'visibility',
            'urls',
            'uuid_b58',
        },
        'without_parent': {
            'name',
            'title',
            'number',
            'body',
            'body_text',
            'body_html',
            'published_at',
            'edited_at',
            'created_by',
            'is_pinned',
            'is_currently_restricted',
            'visibility',
            'urls',
            'uuid_b58',
        },
        'related': {'name', 'title', 'urls'},
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.commentset = Commentset(settype=SET_TYPE.UPDATE)

    def __repr__(self) -> str:
        """Represent :class:`Update` as a string."""
        return f'<Update "{self.title}" {self.uuid_b58}>'

    @role_check('reader')
    def has_reader_role(self, actor: Account | None) -> bool:
        """Check if the given actor is a reader based on the Update's visibility."""
        if not self.state.PUBLISHED:
            # Update must be published to allow anyone other than crew to read
            return False
        if self.visibility_state.PUBLIC:
            return True
        roles = self.roles_for(actor)
        if self.visibility_state.PARTICIPANTS:
            return 'project_participant' in roles
        if self.visibility_state.MEMBERS:
            return 'account_member' in roles

        raise RuntimeError("This update has an unexpected state")

    # 'reader' is a non-enumerated role, like `all`, `auth` and `anon`

    @property
    def visibility(self) -> str:
        """Return visibility state name."""
        return self.visibility_state.label.name

    @visibility.setter
    def visibility(self, value: str) -> None:
        """Set visibility state (interim until visibility as state is resolved)."""
        # FIXME: Move to using an Enum so we don't reproduce the enumeration here
        match value:
            case 'public':
                vstate = VISIBILITY_STATE.PUBLIC
            case 'participants':
                vstate = VISIBILITY_STATE.PARTICIPANTS
            case 'members':
                vstate = VISIBILITY_STATE.MEMBERS
            case _:
                raise ValueError("Unknown visibility state")
        self._visibility_state = vstate  # type: ignore[assignment]

    with_roles(visibility, read={'all'}, write={'editor'})

    state.add_conditional_state(
        'UNPUBLISHED',
        state.DRAFT,
        lambda update: update.published_at is None,
        lambda update: update.published_at.is_(None),
        label=('unpublished', __("Unpublished")),
    )

    state.add_conditional_state(
        'WITHDRAWN',
        state.DRAFT,
        lambda update: update.published_at is not None,
        lambda update: update.published_at.is_not(None),
        label=('withdrawn', __("Withdrawn")),
    )

    @with_roles(call={'editor'})
    @state.transition(state.DRAFT, state.PUBLISHED)
    def publish(self, actor: Account) -> bool:
        first_publishing = False
        self.published_by = actor
        if self.published_at is None:
            first_publishing = True
            self.published_at = sa.func.utcnow()
        if self.number is None:
            self.number = (
                sa.select(sa.func.coalesce(sa.func.max(Update.number), 0) + 1)
                .where(Update.project == self.project)
                .scalar_subquery()
            )
        return first_publishing

    @with_roles(call={'editor'})
    @state.transition(state.PUBLISHED, state.DRAFT)
    def undo_publish(self) -> None:
        pass

    @with_roles(call={'creator', 'editor'})
    @state.transition(None, state.DELETED)
    def delete(self, actor: Account) -> None:
        if self.state.UNPUBLISHED:
            # If it was never published, hard delete it
            db.session.delete(self)
        else:
            # If published, then soft delete
            self.deleted_by = actor
            self.deleted_at = sa.func.utcnow()

    @with_roles(call={'editor'})
    @state.transition(state.DELETED, state.DRAFT)
    def undelete(self) -> None:
        self.deleted_by = None
        self.deleted_at = None

    @property
    def is_currently_restricted(self) -> bool:
        """Check if this update is not available for the current user."""
        return not self.current_roles.reader

    with_roles(is_currently_restricted, read={'all'})

    @classmethod
    def all_published_public(cls) -> Query[Self]:
        return cls.query.join(Project).filter(
            Project.state.PUBLISHED, cls.state.PUBLISHED, cls.visibility_state.PUBLIC
        )

    @with_roles(read={'all'})
    def getnext(self) -> Update | None:
        """Get next published update."""
        if self.state.PUBLISHED:
            return (
                Update.query.filter(
                    Update.project == self.project,
                    Update.state.PUBLISHED,
                    Update.number > self.number,
                )
                .order_by(Update.number.asc())
                .first()
            )
        return None

    @with_roles(read={'all'})
    def getprev(self) -> Update | None:
        """Get previous published update."""
        if self.state.PUBLISHED:
            return (
                Update.query.filter(
                    Update.project == self.project,
                    Update.state.PUBLISHED,
                    Update.number < self.number,
                )
                .order_by(Update.number.desc())
                .first()
            )
        return None


add_search_trigger(Update, 'search_vector')
auto_init_default(Update._visibility_state)  # pylint: disable=protected-access
auto_init_default(Update._state)  # pylint: disable=protected-access
