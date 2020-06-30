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

__all__ = ['Blogpost']


class BLOGPOST_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    DELETED = (2, 'deleted', __("Deleted"))


class VISIBILITY_CHOICES(LabeledEnum):  # NOQA: N801
    PUBLIC = (0, 'public', __("Public"))
    PARTICIPANTS = (1, 'participants', __("Participants only"))
    CREW = (2, 'crew_only', __("Crew only"))


class Blogpost(UuidMixin, BaseMixin, TimestampMixin, db.Model):
    __tablename__ = 'blogpost'

    visibility = db.Column(
        db.Integer,
        StateManager.check_constraint('record_type', VISIBILITY_CHOICES),
        default=VISIBILITY_CHOICES.PUBLIC,
        nullable=False,
    )

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', BLOGPOST_STATE),
        default=BLOGPOST_STATE.DRAFT,
        nullable=False,
    )
    state = StateManager('_state', BLOGPOST_STATE, doc="Blogpost state")

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, index=True)
    user = with_roles(
        db.relationship(
            User,
            primaryjoin=user_id == User.id,
            backref=db.backref('blogposts', cascade='all', lazy='dynamic'),
        ),
        grants={'author'},
    )

    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=True, index=True)
    profile = with_roles(
        db.relationship(
            Profile,
            primaryjoin=profile_id == Profile.id,
            backref=db.backref('blogposts', cascade='all', lazy='dynamic'),
        ),
        grants_via={None: {'admin': 'profile_admin'}},
    )

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=True, index=True)
    project = with_roles(
        db.relationship(
            Project,
            primaryjoin=project_id == Project.id,
            backref=db.backref('blogposts', cascade='all', lazy='dynamic'),
        ),
        grants_via={None: {'editor': 'project_editor'}},
    )

    body = MarkdownColumn('message', nullable=False)

    #: Like pinned tweets. You can keep posting updates,
    #: but might want to pin an update from a week ago.
    pinned = db.Column(db.Boolean, default=False, nullable=False)

    published_by_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=True, index=True
    )
    published_by = db.relationship(User, primaryjoin=published_by_id == User.id)
    published_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    deleted_by_id = db.Column(None, db.ForeignKey('user.id'), nullable=True, index=True)
    deleted_by = db.relationship(User, primaryjoin=deleted_by_id == User.id)
    deleted_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(
        Commentset,
        uselist=False,
        lazy='joined',
        cascade='all',
        single_parent=True,
        backref=db.backref('blogpost', uselist=False),
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
                    ' / ', Blogpost.title, Blogpost.body_html,
                ),
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        # FIXME: Should we check for user_id as well? That would allow users to
        # post blog posts in future in their own profile
        db.CheckConstraint(
            db.case([(profile_id.isnot(None), 1)], else_=0)
            + db.case([(project_id.isnot(None), 1)], else_=0)
            == 1,
            name='blogpost_owner_check',
        ),
    )

    __roles__ = {
        'all': {
            'read': {
                'body',
                'created_at',
                'edited_at',
                'name',
                'title',
                'user',
                'visibility',
            }
        }
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
        self.voteset = Voteset(settype=SET_TYPE.BLOGPOST)
        self.commentset = Commentset(settype=SET_TYPE.BLOGPOST)

    def __repr__(self):
        return '<Blogpost "{title}" {uuid_b58}'.format(
            title=self.title, uuid_b58=self.uuid_b58
        )

    @with_roles(call={'author', 'profile_admin', 'project_editor'})
    @state.transition(
        state.DRAFT,
        state.PUBLISHED,
        title=__("Publish blogpost"),
        message=__("Blogpost has been published"),
    )
    def publish(self, actor):
        self.published_by = actor
        self.published_at = db.func.utcnow()

    @with_roles(call={'author', 'profile_admin', 'project_editor'})
    @state.transition(
        state.PUBLISHED,
        state.DRAFT,
        title=__("Undo publish"),
        message=__("Blogpost is now a draft"),
    )
    def undo_publish(self):
        self.published_by = None
        self.published_at = None

    @with_roles(call={'author', 'profile_admin', 'project_editor'})
    @state.transition(
        None,
        state.DELETED,
        title=__("Delete blogpost"),
        message=__("Blogpost has been deleted"),
    )
    def delete(self, actor):
        self.deleted_by = actor
        self.deleted_at = db.func.utcnow()

    @with_roles(call={'author', 'profile_admin', 'project_editor'})
    @state.transition(
        state.DELETED,
        state.DRAFT,
        title=__("Undo delete"),
        message=__("Blogpost is now a draft"),
    )
    def undo_delete(self):
        self.deleted_by = None
        self.deleted_at = None
