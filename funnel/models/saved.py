"""Models for user bookmarks of projects and sessions."""

from __future__ import annotations

from datetime import datetime

from coaster.sqlalchemy import with_roles

from .account import Account
from .base import Mapped, Model, NoIdMixin, db, relationship, sa, sa_orm
from .project import Project
from .session import Session


class SavedProject(NoIdMixin, Model):
    __tablename__ = 'saved_project'

    #: User account that saved this project
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        default=None,
        nullable=False,
        primary_key=True,
    )
    account: Mapped[Account] = with_roles(
        relationship(back_populates='saved_projects'), grants={'owner'}
    )
    #: Project that was saved
    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id', ondelete='CASCADE'),
        default=None,
        nullable=False,
        primary_key=True,
        index=True,
    )
    project: Mapped[Project] = relationship(back_populates='saves')
    #: Timestamp when the save happened
    saved_at: Mapped[datetime] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        insert_default=sa.func.utcnow(),
        default=None,
    )
    #: User's plaintext note to self on why they saved this (optional)
    description: Mapped[str | None] = sa_orm.mapped_column(
        sa.UnicodeText, nullable=True
    )

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        project_ids = {sp.project_id for sp in new_account.saved_projects}
        for sp in old_account.saved_projects:
            if sp.project_id not in project_ids:
                sp.account = new_account
            else:
                db.session.delete(sp)


class SavedSession(NoIdMixin, Model):
    __tablename__ = 'saved_session'

    #: User account that saved this session
    account_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id', ondelete='CASCADE'),
        default=None,
        nullable=False,
        primary_key=True,
    )
    account: Mapped[Account] = with_roles(
        relationship(back_populates='saved_sessions'), grants={'owner'}
    )
    #: Session that was saved
    session_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('session.id', ondelete='CASCADE'),
        default=None,
        nullable=False,
        primary_key=True,
        index=True,
    )
    session: Mapped[Session] = relationship(back_populates='saves')
    #: Timestamp when the save happened
    saved_at: Mapped[datetime] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        insert_default=sa.func.utcnow(),
        default=None,
    )
    #: User's plaintext note to self on why they saved this (optional)
    description: Mapped[str | None] = sa_orm.mapped_column(
        sa.UnicodeText, nullable=True
    )

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        session_ids = {ss.session_id for ss in new_account.saved_sessions}
        for ss in old_account.saved_sessions:
            if ss.session_id not in session_ids:
                ss.account = new_account
            else:
                # TODO: `if ss.description`, don't discard, but add it to existing's
                # description
                db.session.delete(ss)
