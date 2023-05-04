"""Models for user bookmarks of projects and sessions."""

from __future__ import annotations

from typing import Iterable, Optional

from coaster.sqlalchemy import LazyRoleSet, with_roles

from . import Mapped, NoIdMixin, db, sa
from .account import Account
from .helpers import reopen
from .project import Project
from .session import Session


class SavedProject(NoIdMixin, db.Model):  # type: ignore[name-defined]
    #: User who saved this project
    user_id: Mapped[int] = sa.Column(
        sa.Integer,
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    user: Mapped[Account] = sa.orm.relationship(
        Account,
        backref=sa.orm.backref('saved_projects', lazy='dynamic', passive_deletes=True),
    )
    #: Project that was saved
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('project.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
        index=True,
    )
    project: Mapped[Project] = sa.orm.relationship(
        Project,
        backref=sa.orm.backref('saved_by', lazy='dynamic', passive_deletes=True),
    )
    #: Timestamp when the save happened
    saved_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )
    #: User's plaintext note to self on why they saved this (optional)
    description = sa.Column(sa.UnicodeText, nullable=True)

    def roles_for(
        self, actor: Optional[Account] = None, anchors: Iterable = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('owner')
        return roles

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        project_ids = {sp.project_id for sp in new_account.saved_projects}
        for sp in old_account.saved_projects:
            if sp.project_id not in project_ids:
                sp.user = new_account
            else:
                db.session.delete(sp)


class SavedSession(NoIdMixin, db.Model):  # type: ignore[name-defined]
    #: User who saved this session
    user_id: Mapped[int] = sa.Column(
        sa.Integer,
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    user: Mapped[Account] = sa.orm.relationship(
        Account,
        backref=sa.orm.backref('saved_sessions', lazy='dynamic', passive_deletes=True),
    )
    #: Session that was saved
    session_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('session.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
        index=True,
    )
    session: Mapped[Session] = sa.orm.relationship(
        Session,
        backref=sa.orm.backref('saved_by', lazy='dynamic', passive_deletes=True),
    )
    #: Timestamp when the save happened
    saved_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, default=sa.func.utcnow()
    )
    #: User's plaintext note to self on why they saved this (optional)
    description = sa.Column(sa.UnicodeText, nullable=True)

    def roles_for(
        self, actor: Optional[Account] = None, anchors: Iterable = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('owner')
        return roles

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        project_ids = {ss.project_id for ss in new_account.saved_sessions}
        for ss in old_account.saved_sessions:
            if ss.project_id not in project_ids:
                ss.user = new_account
            else:
                # TODO: `if ss.description`, don't discard, but add it to existing's
                # description
                db.session.delete(ss)


@reopen(Account)
class __Account:
    def saved_sessions_in(self, project):
        return self.saved_sessions.join(Session).filter(Session.project == project)


@reopen(Project)
class __Project:
    @with_roles(call={'all'})
    def is_saved_by(self, user):
        return (
            user is not None and self.saved_by.filter_by(user=user).first() is not None
        )
