from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from . import (
    BaseMixin,
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

__all__ = ['Post']


class POST_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    DELETED = (2, 'deleted', __("Deleted"))


class VISIBILITY_STATE(LabeledEnum):  # NOQA: N801
    PUBLIC = (0, 'public', __("Public"))
    RESTRICTED = (1, 'restricted', __("Restricted"))


class Post(UuidMixin, BaseMixin, TimestampMixin, db.Model):
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
        grants_via={None: {'admin': 'profile_admin'}},
    )

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=True, index=True)
    project = with_roles(
        db.relationship(Project, backref=db.backref('posts', lazy='dynamic'),),
        grants_via={None: {'editor': 'project_editor'}},
    )

    body = MarkdownColumn('body', nullable=False)

    #: Like pinned tweets. You can keep posting updates,
    #: but might want to pin an update from a week ago.
    pinned = db.Column(db.Boolean, default=False, nullable=False)

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
                hltext=lambda: db.func.concat_ws(' / ', Post.title, Post.body_html,),
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
        'all': {'read': {'name', 'title'}},
        'reader': {'read': {'body', 'created_at', 'edited_at', 'user', 'visibility'}},
    }

    __datasets__ = {
        'primary': {
            'body',
            'created_at',
            'edited_at',
            'name',
            'title',
            'user',
            'visibility',
        }
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.POST)
        self.commentset = Commentset(settype=SET_TYPE.POST)

    def __repr__(self):
        return '<Post "{title}" {uuid_b58}'.format(
            title=self.title, uuid_b58=self.uuid_b58
        )

    state.add_conditional_state(
        'UNPUBLISHED',
        state.DRAFT,
        lambda post: post.published_at is not None,
        lambda post: post.published_at.isnot(None),
        label=('unpublished', __("Unpublished")),
    )

    @with_roles(call={'creator', 'profile_admin', 'project_editor'})
    @state.transition(
        state.DRAFT,
        state.PUBLISHED,
        title=__("Publish post"),
        message=__("Post has been published"),
    )
    def publish(self, actor):
        self.published_by = actor
        if self.published_at is None:
            self.published_at = db.func.utcnow()

    @with_roles(call={'creator', 'profile_admin', 'project_editor'})
    @state.transition(
        state.PUBLISHED,
        state.DRAFT,
        title=__("Undo publish"),
        message=__("Post is now a draft"),
    )
    def undo_publish(self):
        pass

    @with_roles(call={'creator', 'profile_admin', 'project_editor'})
    @state.transition(
        None,
        state.DELETED,
        title=__("Delete post"),
        message=__("Post has been deleted"),
    )
    def delete(self, actor):
        if self.state.DRAFT:
            # If it's a draft post, hard delete it
            db.session.delete(self)
        else:
            # If not, then soft delete
            self.deleted_by = actor
            self.deleted_at = db.func.utcnow()

    @with_roles(call={'creator', 'profile_admin', 'project_editor'})
    @state.transition(
        state.DELETED,
        state.DRAFT,
        title=__("Undo delete"),
        message=__("Post is now a draft"),
    )
    def undo_delete(self):
        self.deleted_by = None
        self.deleted_at = None

    @with_roles(call={'creator', 'profile_admin', 'project_editor'})
    @visibility_state.transition(
        visibility_state.RESTRICTED,
        visibility_state.PUBLIC,
        title=__("Make post public"),
        message=__("Post is now public"),
    )
    def make_public(self):
        pass

    @with_roles(call={'creator', 'profile_admin', 'project_editor'})
    @visibility_state.transition(
        visibility_state.PUBLIC,
        visibility_state.RESTRICTED,
        title=__("Make post restricted"),
        message=__("Post is now restricted"),
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

        if 'editor' in project_roles:
            roles.add('editor')
        if 'admin' in profile_roles:
            roles.add('admin')

        return roles
