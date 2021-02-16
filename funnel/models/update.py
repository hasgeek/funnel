from __future__ import annotations

from typing import Iterable, Optional, Set

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Query as BaseQuery

from baseframe import __
from coaster.sqlalchemy import (
    Query,
    StateManager,
    auto_init_default,
    immutable,
    with_roles,
)
from coaster.utils import LabeledEnum

from . import (
    BaseScopedIdNameMixin,
    Commentset,
    MarkdownColumn,
    NoIdMixin,
    Project,
    TSVectorType,
    User,
    UuidMixin,
    Voteset,
    db,
)
from .commentvote import SET_TYPE
from .helpers import add_search_trigger, reopen, visual_field_delimiter

__all__ = ['Update']


class UPDATE_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    DELETED = (2, 'deleted', __("Deleted"))


class VISIBILITY_STATE(LabeledEnum):  # NOQA: N801
    PUBLIC = (0, 'public', __("Public"))
    RESTRICTED = (1, 'restricted', __("Restricted"))
    PROMOTION = (2, 'promotion', __("Promotion"))

    REGULAR = {PUBLIC, RESTRICTED}


class Update(UuidMixin, BaseScopedIdNameMixin, db.Model):
    __tablename__ = 'update'

    _visibility_state = db.Column(
        'visibility_state',
        db.SmallInteger,
        StateManager.check_constraint('visibility_state', VISIBILITY_STATE),
        default=VISIBILITY_STATE.PUBLIC,
        nullable=False,
        index=True,
    )
    visibility_state = StateManager(
        '_visibility_state', VISIBILITY_STATE, doc="Visibility state"
    )

    _state = db.Column(
        'state',
        db.SmallInteger,
        StateManager.check_constraint('state', UPDATE_STATE),
        default=UPDATE_STATE.DRAFT,
        nullable=False,
        index=True,
    )
    state = StateManager('_state', UPDATE_STATE, doc="Update state")

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, index=True)
    user = with_roles(
        db.relationship(
            User, backref=db.backref('updates', lazy='dynamic'), foreign_keys=[user_id]
        ),
        read={'all'},
        grants={'creator'},
    )

    project_id = db.Column(
        None, db.ForeignKey('project.id'), nullable=False, index=True
    )
    project = with_roles(
        db.relationship(Project, backref=db.backref('updates', lazy='dynamic')),
        read={'all'},
        grants_via={
            None: {
                'editor': {'reader', 'editor', 'project_editor'},
                'promoter': {'reader', 'promoter', 'project_promoter'},
                'participant': {'reader', 'project_participant'},
                'crew': {'reader', 'project_crew'},
            }
        },
    )
    parent = db.synonym('project')

    update_promotions = with_roles(
        db.relationship('UpdatePromotion'),
        read={'all'},
        grants_via={None: {'promoted_participant'}},
    )

    body = MarkdownColumn('body', nullable=False)

    #: Update number, for Project updates, assigned when the update is published
    number = with_roles(
        db.Column(db.Integer, nullable=True, default=None), read={'all'}
    )

    #: Like pinned tweets. You can keep posting updates,
    #: but might want to pin an update from a week ago.
    is_pinned = with_roles(
        db.Column(db.Boolean, default=False, nullable=False), read={'all'}
    )

    published_by_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=True, index=True
    )
    published_by = with_roles(
        db.relationship(
            User,
            backref=db.backref('published_updates', lazy='dynamic'),
            foreign_keys=[published_by_id],
        ),
        read={'all'},
    )
    published_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True), read={'all'}
    )

    deleted_by_id = db.Column(None, db.ForeignKey('user.id'), nullable=True, index=True)
    deleted_by = with_roles(
        db.relationship(
            User,
            backref=db.backref('deleted_updates', lazy='dynamic'),
            foreign_keys=[deleted_by_id],
        ),
        read={'reader'},
    )
    deleted_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True), read={'reader'}
    )

    edited_at = with_roles(
        db.Column(db.TIMESTAMP(timezone=True), nullable=True), read={'all'}
    )

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = with_roles(db.relationship(Voteset, uselist=False), read={'all'})

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = with_roles(
        db.relationship(
            Commentset,
            uselist=False,
            lazy='joined',
            cascade='all',
            single_parent=True,
            backref=db.backref('update', uselist=False),
        ),
        read={'all'},
    )

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'name',
                'title',
                'body_text',
                weights={'name': 'A', 'title': 'A', 'body_text': 'B'},
                regconfig='english',
                hltext=lambda: db.func.concat_ws(
                    visual_field_delimiter, Update.title, Update.body_html
                ),
            ),
            nullable=False,
        )
    )

    __roles__ = {
        'all': {
            'read': {'name', 'title', 'urls'},
            'call': {'features', 'visibility_state', 'state', 'url_for'},
        },
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
            'user',
            'is_pinned',
            'is_restricted',
            'is_currently_restricted',
            'visibility_label',
            'state_label',
            'urls',
            'uuid_b58',
        },
        'related': {'name', 'title', 'urls'},
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.UPDATE)
        self.commentset = Commentset(settype=SET_TYPE.UPDATE)

    def __repr__(self) -> str:
        """Represent :class:`Update` as a string."""
        return '<Update "{title}" {uuid_b58}>'.format(
            title=self.title, uuid_b58=self.uuid_b58
        )

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def visibility_label(self) -> str:
        return self.visibility_state.label.title

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def state_label(self) -> str:
        return self.state.label.title

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
        lambda update: update.published_at.isnot(None),
        label=('withdrawn', __("Withdrawn")),
    )

    @with_roles(call={'editor', 'promoter'})
    @state.transition(state.DRAFT, state.PUBLISHED)
    def publish(self, actor: User) -> bool:
        first_publishing = False
        self.published_by = actor
        if self.published_at is None:
            first_publishing = True
            self.published_at = db.func.utcnow()
        if self.number is None and not self.visibility_state.PROMOTION:
            # Assign a number only if:
            # 1. It doesn't have a number already, and
            # 2. It's not a promotion.
            # Sequential numbers are a tracking tool for project participants and don't
            # apply in unpublished updates or promotions.
            self.number = db.select(
                [db.func.coalesce(db.func.max(Update.number), 0) + 1]
            ).where(Update.project == self.project)
        return first_publishing

    @with_roles(call={'editor'})
    @state.transition(state.PUBLISHED, state.DRAFT)
    def undo_publish(self) -> None:
        pass

    @with_roles(call={'creator', 'editor'})
    @state.transition(None, state.DELETED)
    def delete(self, actor: User) -> None:
        if self.state.UNPUBLISHED:
            # If it was never published, hard delete it
            db.session.delete(self)
        else:
            # If not, then soft delete
            self.deleted_by = actor
            self.deleted_at = db.func.utcnow()

    @with_roles(call={'editor', 'promoter'})
    @state.transition(state.DELETED, state.DRAFT)
    def undo_delete(self) -> None:
        self.deleted_by = None
        self.deleted_at = None

    @with_roles(call={'editor'})
    @visibility_state.transition(visibility_state.RESTRICTED, visibility_state.PUBLIC)
    def make_public(self) -> None:
        pass

    @with_roles(call={'editor'})
    @visibility_state.transition(visibility_state.PUBLIC, visibility_state.RESTRICTED)
    def make_restricted(self) -> None:
        pass

    @with_roles(call={'promoter'})
    @state.requires(state.UNPUBLISHED)
    @visibility_state.transition(visibility_state.REGULAR, visibility_state.PROMOTION)
    def make_promotion(self) -> None:
        pass

    @with_roles(call={'editor'})
    @state.requires(state.UNPUBLISHED)
    @visibility_state.transition(visibility_state.PROMOTION, visibility_state.PUBLIC)
    def make_regular(self) -> None:
        pass

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def is_restricted(self) -> bool:
        return bool(self.visibility_state.RESTRICTED)

    @is_restricted.setter
    def is_restricted(self, value: bool) -> None:
        if value and self.visibility_state.PUBLIC:
            self.make_restricted()
        elif not value and self.visibility_state.RESTRICTED:
            self.make_public()

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def is_currently_restricted(self) -> bool:
        return self.is_restricted and not self.current_roles.reader

    def roles_for(self, actor: Optional[User], anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        if not self.visibility_state.RESTRICTED:
            # Everyone gets reader role when the post is not restricted.
            # If it is, 'reader' must be mapped from 'participant' in the project,
            # specified above in the grants_via annotation on project.
            roles.add('reader')

        return roles

    @classmethod
    def all_published_public(cls) -> Query:
        return cls.query.join(Project).filter(
            Project.state.PUBLISHED, cls.state.PUBLISHED, cls.visibility_state.PUBLIC
        )


add_search_trigger(Update, 'search_vector')
auto_init_default(Update._visibility_state)
auto_init_default(Update._state)


class UpdatePromotion(NoIdMixin, db.Model):
    """Holds an authorization allowing an update to be promoted to a project."""

    __tablename__ = 'update_promotion'
    update_id = immutable(
        db.Column(
            None, db.ForeignKey('update.id', ondelete='CASCADE'), primary_key=True
        )
    )
    update = immutable(db.relationship(Update))
    project_id = immutable(
        db.Column(
            None, db.ForeignKey('project.id', ondelete='CASCADE'), primary_key=True
        )
    )
    project = with_roles(
        db.relationship(
            Project, backref=db.backref('update_promotions', lazy='dynamic')
        ),
        read={'all'},
        grants_via={
            None: {
                'participant': 'promoted_participant',
                'crew': 'promoted_participant',
            }
        },
    )

    requested_by_id = immutable(
        db.Column(None, db.ForeignKey('user.id'), nullable=False)
    )
    requested_by = immutable(db.relationship(User, foreign_keys=[requested_by_id]))
    requested_at = immutable(
        db.Column(db.TIMESTAMP(timezone=True), default=db.func.utcnow(), nullable=False)
    )

    granted_by_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    granted_by = db.relationship(User, foreign_keys=[granted_by_id])
    granted_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    revoked_by_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    revoked_by = db.relationship(User, foreign_keys=[revoked_by_id])
    revoked_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    @hybrid_property
    def is_active(self):
        return self.granted_at is not None and self.revoked_at is None

    @is_active.expression  # type: ignore[no-redef]
    def is_active(cls):  # NOQA: N805
        return db.and_(
            cls.granted_at.isnot(None),
            cls.revoked_at.is_(None),
        )


@reopen(Project)
class Project:  # type: ignore[no-redef]  # skipcq: PYL-E0102
    updates: BaseQuery

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def published_updates(self) -> BaseQuery:
        return self.updates.filter(Update.state.PUBLISHED).order_by(
            Update.is_pinned.desc(), Update.published_at.desc()
        )

    @with_roles(read={'editor'})  # type: ignore[misc]
    @property
    def draft_updates(self) -> BaseQuery:
        return self.updates.filter(Update.state.DRAFT).order_by(Update.created_at)

    @with_roles(read={'all'})  # type: ignore[misc]
    @property
    def pinned_update(self) -> Optional[Update]:
        return (
            self.updates.filter(Update.state.PUBLISHED, Update.is_pinned.is_(True))
            .order_by(Update.published_at.desc())
            .first()
        )
