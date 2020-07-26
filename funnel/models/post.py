from sqlalchemy.ext.hybrid import hybrid_property

from baseframe import __
from baseframe.filters import age
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from . import (
    BaseScopedIdNameMixin,
    Commentset,
    MarkdownColumn,
    Profile,
    Project,
    TimestampMixin,
    TSVectorType,
    User,
    UuidMixin,
    Voteset,
    db,
)
from .commentvote import SET_TYPE
from .helpers import visual_field_delimiter

__all__ = ['Post']


class POST_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    DELETED = (2, 'deleted', __("Deleted"))


class VISIBILITY_STATE(LabeledEnum):  # NOQA: N801
    PUBLIC = (0, 'public', __("Public"))
    RESTRICTED = (1, 'restricted', __("Restricted"))


class Post(UuidMixin, BaseScopedIdNameMixin, TimestampMixin, db.Model):
    __tablename__ = 'post'

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
        StateManager.check_constraint('state', POST_STATE),
        default=POST_STATE.DRAFT,
        nullable=False,
        index=True,
    )
    state = StateManager('_state', POST_STATE, doc="Post state")

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, index=True)
    user = with_roles(
        db.relationship(
            User, backref=db.backref('posts', lazy='dynamic'), foreign_keys=[user_id],
        ),
        grants={'creator'},
    )

    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=True, index=True)
    profile = with_roles(
        db.relationship(Profile, backref=db.backref('posts', lazy='dynamic'),),
        grants_via={None: {'admin': 'editor'}},
    )

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=True, index=True)
    project = with_roles(
        db.relationship(Project, backref=db.backref('posts', lazy='dynamic'),),
        grants_via={None: {'editor': 'editor'}},
    )

    body = MarkdownColumn('body', nullable=False)

    #: Update number, for Project updates, assigned when the post is published
    number = db.Column(db.Integer, nullable=True, default=None)

    #: Like pinned tweets. You can keep posting updates,
    #: but might want to pin an update from a week ago.
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)

    published_by_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=True, index=True
    )
    published_by = db.relationship(
        User,
        backref=db.backref('published_posts', lazy='dynamic'),
        foreign_keys=[published_by_id],
    )
    published_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    deleted_by_id = db.Column(None, db.ForeignKey('user.id'), nullable=True, index=True)
    deleted_by = db.relationship(
        User,
        backref=db.backref('deleted_posts', lazy='dynamic'),
        foreign_keys=[deleted_by_id],
    )
    deleted_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    edited_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(
        Commentset,
        uselist=False,
        lazy='joined',
        cascade='all',
        single_parent=True,
        backref=db.backref('post', uselist=False),
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
                    visual_field_delimiter, Post.title, Post.body_html
                ),
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        db.CheckConstraint(
            db.case([(profile_id.isnot(None), 1)], else_=0)
            + db.case([(project_id.isnot(None), 1)], else_=0)
            == 1,
            name='post_owner_check',
        ),
    )

    __roles__ = {
        'all': {
            'read': {
                'name',
                'title',
                'number',
                'user',
                'published_at',
                'published_at_age',
                'edited_at',
                'edited_at_age',
                'deleted_at',
                'deleted_at_age',
                'visibility_label',
                'state_label',
                'urls',
            },
            'call': {'features', 'visibility_state', 'state', 'url_for'},
        },
        'reader': {'read': {'body'}},
    }

    __datasets__ = {
        'primary': {
            'name',
            'title',
            'number',
            'body_text',
            'published_at',
            'published_at_age',
            'edited_at',
            'edited_at_age',
            'user',
            'visibility_label',
            'state_label',
        }
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.POST)
        self.commentset = Commentset(settype=SET_TYPE.POST)

    def __repr__(self):
        return '<Post "{title}" {uuid_b58}>'.format(
            title=self.title, uuid_b58=self.uuid_b58
        )

    @hybrid_property
    def parent(self):
        return self.project if self.project is not None else self.profile

    @parent.setter
    def parent(self, value):
        if not isinstance(value, (Project, Profile)):
            raise ValueError("Only a project or a profile can be parent of a post")

        if self.project is not None:
            self.project = value
        else:
            self.profile = value

    @hybrid_property
    def published_at_age(self):
        return age(self.created_at)

    @hybrid_property
    def edited_at_age(self):
        return age(self.edited_at) if self.edited_at is not None else None

    @hybrid_property
    def deleted_at_age(self):
        return age(self.deleted_at) if self.deleted_at is not None else None

    @hybrid_property
    def visibility_label(self):
        return self.visibility_state.label.title

    @hybrid_property
    def state_label(self):
        return self.state.label.title

    state.add_conditional_state(
        'UNPUBLISHED',
        state.DRAFT,
        lambda post: post.published_at is not None,
        lambda post: post.published_at.isnot(None),
        label=('unpublished', __("Unpublished")),
    )

    @with_roles(call={'editor'})
    @state.transition(
        state.DRAFT, state.PUBLISHED,
    )
    def publish(self, actor):
        self.published_by = actor
        if self.published_at is None:
            self.published_at = db.func.utcnow()
        if self.number is None:
            self.number = db.select(
                [db.func.coalesce(db.func.max(Post.number), 0) + 1]
            ).where(
                (Post.project == self.project)
                if self.project is not None
                else (Post.profile == self.profile)
            )

    @with_roles(call={'editor'})
    @state.transition(
        state.PUBLISHED, state.DRAFT,
    )
    def undo_publish(self):
        pass

    @with_roles(call={'creator', 'editor'})
    @state.transition(
        None, state.DELETED,
    )
    def delete(self, actor):
        if self.state.DRAFT and self.published_at is not None:
            # If it was never published, hard delete it
            db.session.delete(self)
        else:
            # If not, then soft delete
            self.deleted_by = actor
            self.deleted_at = db.func.utcnow()

    @with_roles(call={'editor'})
    @state.transition(
        state.DELETED, state.DRAFT,
    )
    def undo_delete(self):
        self.deleted_by = None
        self.deleted_at = None

    @with_roles(call={'editor'})
    @visibility_state.transition(
        visibility_state.RESTRICTED, visibility_state.PUBLIC,
    )
    def make_public(self):
        pass

    @with_roles(call={'editor'})
    @visibility_state.transition(
        visibility_state.PUBLIC, visibility_state.RESTRICTED,
    )
    def make_restricted(self):
        pass

    def roles_for(self, actor=None, anchors=()):
        roles = super().roles_for(actor, anchors)
        project_roles = (
            self.project.roles_for(actor) if self.project is not None else set()
        )
        profile_roles = (
            self.profile.roles_for(actor) if self.profile is not None else set()
        )

        if self.visibility_state.RESTRICTED:
            if 'participant' in project_roles or 'admin' in profile_roles:
                roles.add('reader')
        else:
            roles.add('reader')

        return roles


Project.published_posts = db.relationship(
    Post,
    lazy='dynamic',
    primaryjoin=db.and_(Post.project_id == Project.id, Post.state.PUBLISHED),
    viewonly=True,
    order_by=(Post.is_pinned.desc(), Post.published_at.desc()),
)


Project.draft_posts = db.relationship(
    Post,
    lazy='dynamic',
    primaryjoin=db.and_(Post.project_id == Project.id, Post.state.DRAFT),
    viewonly=True,
    order_by=Post.published_at.desc(),
)

Project.pinned_posts = db.relationship(
    Post,
    lazy='dynamic',
    primaryjoin=db.and_(
        Post.project_id == Project.id, Post.state.PUBLISHED, Post.is_pinned.is_(True)
    ),
    viewonly=True,
    order_by=Post.published_at.desc(),
)
