"""Legacy project registration model, storing RSVP states (Y/N/M/A)."""

from __future__ import annotations

from typing import Literal, cast, overload

from flask import current_app
from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from . import (
    Mapped,
    Model,
    NoIdMixin,
    Query,
    UuidMixin,
    backref,
    db,
    relationship,
    sa,
    types,
)
from .account import Account, AccountEmail, AccountEmailClaim, AccountPhone
from .helpers import reopen
from .project import Project
from .project_membership import project_child_role_map

__all__ = ['Rsvp', 'RSVP_STATUS']


class RSVP_STATUS(LabeledEnum):  # noqa: N801
    # If you add any new state, you need to add a migration to modify the check
    # constraint
    YES = ('Y', 'yes', __("Going"))
    NO = ('N', 'no', __("Not going"))
    MAYBE = ('M', 'maybe', __("Maybe"))
    AWAITING = ('A', 'awaiting', __("Awaiting"))


class Rsvp(UuidMixin, NoIdMixin, Model):
    __tablename__ = 'rsvp'
    project_id = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), nullable=False, primary_key=True
    )
    project: Mapped[Project] = with_roles(
        relationship(Project, backref=backref('rsvps', cascade='all', lazy='dynamic')),
        read={'owner', 'project_promoter'},
        grants_via={None: project_child_role_map},
        datasets={'primary'},
    )
    participant_id: Mapped[int] = sa.orm.mapped_column(
        sa.ForeignKey('account.id'), nullable=False, primary_key=True
    )
    participant: Mapped[Account] = with_roles(
        relationship(Account, backref=backref('rsvps', cascade='all', lazy='dynamic')),
        read={'owner', 'project_promoter'},
        grants={'owner'},
        datasets={'primary', 'without_parent'},
    )
    form: Mapped[types.jsonb | None] = with_roles(
        sa.orm.mapped_column(),
        rw={'owner'},
        read={'project_promoter'},
        datasets={'primary', 'without_parent', 'related'},
    )

    _state = sa.orm.mapped_column(
        'state',
        sa.CHAR(1),
        StateManager.check_constraint('state', RSVP_STATUS),
        default=RSVP_STATUS.AWAITING,
        nullable=False,
    )
    state = with_roles(
        StateManager('_state', RSVP_STATUS, doc="RSVP answer"),
        call={'owner', 'project_promoter'},
    )

    __roles__ = {
        'owner': {'read': {'created_at', 'updated_at'}},
        'project_promoter': {'read': {'created_at', 'updated_at'}},
    }

    @property
    def response(self):
        """Return RSVP response as a raw value."""
        return self._state

    with_roles(
        response,
        read={'owner', 'project_promoter'},
        datasets={'primary', 'without_parent', 'related'},
    )

    @with_roles(call={'owner'})
    @state.transition(
        None,
        state.YES,
        title=__("Going"),
        message=__("Your response has been saved"),
        type='primary',
    )
    def rsvp_yes(self):
        pass

    @with_roles(call={'owner'})
    @state.transition(
        None,
        state.NO,
        title=__("Not going"),
        message=__("Your response has been saved"),
        type='dark',
    )
    def rsvp_no(self):
        pass

    @with_roles(call={'owner'})
    @state.transition(
        None,
        state.MAYBE,
        title=__("Maybe"),
        message=__("Your response has been saved"),
        type='accent',
    )
    def rsvp_maybe(self):
        pass

    @with_roles(call={'owner'})
    @state.transition(
        None,
        state.AWAITING,
        title=__("Awaiting"),
        message=__("Your response has been saved"),
        type='accent',
    )
    def rsvp_awaiting(self):
        pass

    @with_roles(call={'owner', 'project_promoter'})
    def participant_email(self) -> AccountEmail | None:
        """Participant's preferred email address for this registration."""
        return self.participant.transport_for_email(self.project.account)

    @with_roles(call={'owner', 'project_promoter'})
    def participant_phone(self) -> AccountEmail | None:
        """Participant's preferred phone number for this registration."""
        return self.participant.transport_for_sms(self.project.account)

    @with_roles(call={'owner', 'project_promoter'})
    def best_contact(
        self,
    ) -> tuple[AccountEmail | AccountEmailClaim | AccountPhone | None, str]:
        email = self.participant_email()
        if email:
            return email, 'e'
        phone = self.participant_phone()
        if phone:
            return phone, 'p'
        if self.participant.emailclaims:
            return self.participant.emailclaims[0], 'ec'
        return None, ''

    @classmethod
    def migrate_account(cls, old_account: Account, new_account: Account) -> None:
        """Migrate one account's data to another when merging accounts."""
        project_ids = {rsvp.project_id for rsvp in new_account.rsvps}
        for rsvp in old_account.rsvps:
            if rsvp.project_id not in project_ids:
                rsvp.participant = new_account
            else:
                current_app.logger.warning(
                    "Discarding conflicting RSVP (%s) from %r on %r",
                    rsvp._state,  # pylint: disable=protected-access
                    old_account,
                    rsvp.project,
                )
                db.session.delete(rsvp)

    @overload
    @classmethod
    def get_for(cls, project: Project, user: Account, create: Literal[True]) -> Rsvp:
        ...

    @overload
    @classmethod
    def get_for(
        cls, project: Project, account: Account, create: Literal[False]
    ) -> Rsvp | None:
        ...

    @overload
    @classmethod
    def get_for(
        cls, project: Project, account: Account | None, create=False
    ) -> Rsvp | None:
        ...

    @classmethod
    def get_for(
        cls, project: Project, account: Account | None, create=False
    ) -> Rsvp | None:
        if account is not None:
            result = cls.query.get((project.id, account.id))
            if not result and create:
                result = cls(project=project, participant=account)
                db.session.add(result)
            return result
        return None


@reopen(Project)
class __Project:
    @property
    def active_rsvps(self):
        return self.rsvps.join(Account).filter(Rsvp.state.YES, Account.state.ACTIVE)

    with_roles(
        active_rsvps,
        grants_via={Rsvp.participant: {'participant', 'project_participant'}},
    )

    @overload
    def rsvp_for(self, account: Account, create: Literal[True]) -> Rsvp:
        ...

    @overload
    def rsvp_for(self, account: Account | None, create: Literal[False]) -> Rsvp | None:
        ...

    def rsvp_for(self, account: Account | None, create=False) -> Rsvp | None:
        return Rsvp.get_for(cast(Project, self), account, create)

    def rsvps_with(self, status: str):
        return (
            cast(Project, self)
            .rsvps.join(Account)
            .filter(
                Account.state.ACTIVE,
                Rsvp._state == status,  # pylint: disable=protected-access
            )
        )

    def rsvp_counts(self) -> dict[str, int]:
        return dict(
            db.session.query(
                Rsvp._state,  # pylint: disable=protected-access
                sa.func.count(Rsvp._state),  # pylint: disable=protected-access
            )
            .join(Account)
            .filter(Account.state.ACTIVE, Rsvp.project == self)
            .group_by(Rsvp._state)  # pylint: disable=protected-access
            .all()
        )

    @cached_property
    def rsvp_count_going(self) -> int:
        return (
            cast(Project, self)
            .rsvps.join(Account)
            .filter(Account.state.ACTIVE, Rsvp.state.YES)
            .count()
        )


@reopen(Account)
class __Account:
    @property
    def rsvp_followers(self) -> Query[Account]:
        """All users with an active RSVP in a project."""
        return (
            Account.query.filter(Account.state.ACTIVE)
            .join(Rsvp, Rsvp.participant_id == Account.id)
            .join(Project, Rsvp.project_id == Project.id)
            .filter(Rsvp.state.YES, Project.state.PUBLISHED, Project.account == self)
        )

    with_roles(rsvp_followers, grants={'follower'})
