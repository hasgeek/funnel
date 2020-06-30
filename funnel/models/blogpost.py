from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from . import BaseMixin, MarkdownColumn, Profile, Project, User, UuidMixin, db

__all__ = ['Blogpost']


class BLOGPOST_STATE(LabeledEnum):  # NOQA: N801
    DRAFT = (0, 'draft', __("Draft"))
    PUBLISHED = (1, 'published', __("Published"))
    DELETED = (2, 'deleted', __("Deleted"))


class Blogpost(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'blogpost'
    __uuid_primary_key__ = True

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
    profile = db.relationship(
        Profile,
        primaryjoin=profile_id == Profile.id,
        backref=db.backref('blogposts', cascade='all', lazy='dynamic'),
    )

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=True, index=True)
    project = db.relationship(
        Project,
        primaryjoin=project_id == Project.id,
        backref=db.backref('blogposts', cascade='all', lazy='dynamic'),
    )

    message = MarkdownColumn('message', nullable=False)

    #: Like pinned tweets. You can keep posting updates,
    #: but might want to pin an update from a week ago.
    pinned = db.Column(db.Boolean, default=False, nullable=False)

    published_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True,)

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

    def __repr__(self):
        return '<Blogpost "{title}" {uuid_b58}'.format(
            title=self.title, uuid_b58=self.uuid_b58
        )

    @with_roles(call={'author'})
    @state.transition(
        state.DRAFT,
        state.PUBLISHED,
        title=__("Publish blogpost"),
        message=__("Blogpost has been published"),
    )
    def publish(self):
        self.published_at = db.func.utcnow()

    @with_roles(call={'author'})
    @state.transition(
        state.PUBLISHED,
        state.DRAFT,
        title=__("Undo publish"),
        message=__("Blogpost is now a draft"),
    )
    def undo_publish(self):
        self.published_at = None

    @with_roles(call={'author'})
    @state.transition(
        None,
        state.DELETED,
        title=__("Delete blogpost"),
        message=__("Blogpost has been deleted"),
    )
    def delete(self):
        pass

    @with_roles(call={'author'})
    @state.transition(
        state.DELETED,
        state.DRAFT,
        title=__("Undo delete"),
        message=__("Blogpost is now a draft"),
    )
    def undo_delete(self):
        pass
