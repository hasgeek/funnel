"""Models for user bookmarks of projects and sessions."""

from __future__ import annotations

from typing import Iterable, Optional, Set

from coaster.sqlalchemy import with_roles

from ..typing import OptionalMigratedTables
from . import NoIdMixin, db
from .helpers import reopen
from .project import Project
from .session import Session
from .user import User


class SavedProject(NoIdMixin, db.Model):
    #: User who saved this project
    user_id = db.Column(
        None,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    user = db.relationship(
        User, backref=db.backref('saved_projects', lazy='dynamic', passive_deletes=True)
    )
    #: Project that was saved
    project_id = db.Column(
        None,
        db.ForeignKey('project.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
        index=True,
    )
    project = db.relationship(
        Project, backref=db.backref('saved_by', lazy='dynamic', passive_deletes=True)
    )
    #: Timestamp when the save happened
    saved_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )
    #: User's plaintext note to self on why they saved this (optional)
    description = db.Column(db.UnicodeText, nullable=True)

    def roles_for(self, actor: Optional[User] = None, anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('owner')
        return roles

    @classmethod
    def migrate_user(  # type: ignore[return]
        cls, old_user: User, new_user: User
    ) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        project_ids = {sp.project_id for sp in new_user.saved_projects}
        for sp in old_user.saved_projects:
            if sp.project_id not in project_ids:
                sp.user = new_user
            else:
                db.session.delete(sp)


class SavedSession(NoIdMixin, db.Model):
    #: User who saved this session
    user_id = db.Column(
        None,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    user = db.relationship(
        User, backref=db.backref('saved_sessions', lazy='dynamic', passive_deletes=True)
    )
    #: Session that was saved
    session_id = db.Column(
        None,
        db.ForeignKey('session.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
        index=True,
    )
    session = db.relationship(
        Session, backref=db.backref('saved_by', lazy='dynamic', passive_deletes=True)
    )
    #: Timestamp when the save happened
    saved_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow()
    )
    #: User's plaintext note to self on why they saved this (optional)
    description = db.Column(db.UnicodeText, nullable=True)

    def roles_for(self, actor: Optional[User] = None, anchors: Iterable = ()) -> Set:
        roles = super().roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('owner')
        return roles

    @classmethod
    def migrate_user(  # type: ignore[return]
        cls, old_user: User, new_user: User
    ) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        project_ids = {ss.project_id for ss in new_user.saved_sessions}
        for ss in old_user.saved_sessions:
            if ss.project_id not in project_ids:
                ss.user = new_user
            else:
                # TODO: `if ss.description`, don't discard, but add it to existing's
                # description
                db.session.delete(ss)


@reopen(User)
class __User:
    def saved_sessions_in(self, project):
        return self.saved_sessions.join(Session).filter(Session.project == project)


@reopen(Project)
class __Project:
    @with_roles(call={'all'})
    def is_saved_by(self, user):
        return (
            user is not None and self.saved_by.filter_by(user=user).first() is not None
        )
