"""Legacy project registration model, storing RSVP states (Y/N/M/A)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import ReprEnum
from typing import TYPE_CHECKING, Any, Literal, Self, overload

from flask import current_app

from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import DataclassFromType, LabeledEnum

from . import types
from .account import Account, AccountEmail, AccountEmailClaim, AccountPhone
from .base import (
    Mapped,
    Model,
    NoIdMixin,
    UuidMixin,
    db,
    declared_attr,
    relationship,
    sa,
    sa_orm,
)
from .project import Project
from .project_membership import project_child_role_map

__all__ = ['RSVP_STATUS', 'RsvpStateEnum', 'Rsvp']


class RSVP_STATUS(LabeledEnum):  # noqa: N801
    # If you add any new state, you need to add a migration to modify the check
    # constraint
    YES = ('Y', 'yes', __("Going"))
    NO = ('N', 'no', __("Not going"))
    MAYBE = ('M', 'maybe', __("Maybe"))
    AWAITING = ('A', 'awaiting', __("Awaiting"))


@dataclass(frozen=True)
class _RsvpOptions(DataclassFromType, str):
    """RSVP options."""

    # The empty default is required for Mypy's enum plugin's `Enum.__call__` analysis
    response: str = ''
    label: str = ''


class RsvpStateEnum(_RsvpOptions, ReprEnum):
    YES = 'Y', __("Yes"), __("Going")
    NO = 'N', __("No"), __("Not going")
    MAYBE = 'M', __("Maybe"), __("Maybe")
    AWAITING = 'A', __("Invite"), __("Awaiting")


class Rsvp(UuidMixin, NoIdMixin, Model):
    __tablename__ = 'rsvp'
    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id'), default=None, nullable=False, primary_key=True
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='rsvps'),
        read={'owner', 'project_promoter'},
        grants_via={None: project_child_role_map},
        datasets={'primary'},
    )
    participant_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), default=None, nullable=False, primary_key=True
    )
    participant: Mapped[Account] = with_roles(
        relationship(back_populates='rsvps'),
        read={'owner', 'project_promoter'},
        grants={'owner'},
        datasets={'primary', 'without_parent'},
    )
    form: Mapped[types.jsonb | None] = with_roles(
        sa_orm.mapped_column(),
        rw={'owner'},
        read={'project_promoter'},
        datasets={'primary', 'without_parent', 'related'},
    )

    _state: Mapped[str] = sa_orm.mapped_column(
        'state',
        sa.CHAR(1),
        StateManager.check_constraint('state', RsvpStateEnum, sa.CHAR(1)),
        default=RsvpStateEnum.AWAITING,
        nullable=False,
    )
    state = with_roles(
        StateManager['Rsvp']('_state', RSVP_STATUS, doc="RSVP answer"),
        call={'owner', 'project_promoter'},
    )

    if TYPE_CHECKING:
        id_: declared_attr[Any]  # Fake entry for compatibility with ModelUuidProtocol

    __roles__ = {
        'owner': {'read': {'created_at', 'updated_at'}},
        'project_promoter': {'read': {'created_at', 'updated_at'}},
    }

    @property
    def response(self) -> str:
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
    def rsvp_yes(self) -> None:
        pass

    @with_roles(call={'owner'})
    @state.transition(
        None,
        state.NO,
        title=__("Not going"),
        message=__("Your response has been saved"),
        type='dark',
    )
    def rsvp_no(self) -> None:
        pass

    @with_roles(call={'owner'})
    @state.transition(
        None,
        state.MAYBE,
        title=__("Maybe"),
        message=__("Your response has been saved"),
        type='accent',
    )
    def rsvp_maybe(self) -> None:
        pass

    @with_roles(call={'owner', 'project_promoter'})
    def participant_email(self) -> AccountEmail | None:
        """Participant's preferred email address for this registration."""
        return self.participant.transport_for_email(self.project.account)

    @with_roles(call={'owner', 'project_promoter'})
    def participant_phone(self) -> AccountPhone | None:
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
    def get_for(
        cls, project: Project, account: Account, create: Literal[True]
    ) -> Self: ...

    @overload
    @classmethod
    def get_for(
        cls, project: Project, account: Account, create: Literal[False]
    ) -> Self | None: ...

    @overload
    @classmethod
    def get_for(
        cls, project: Project, account: Account | None, create: bool = False
    ) -> Self | None: ...

    @classmethod
    def get_for(
        cls, project: Project, account: Account | None, create: bool = False
    ) -> Self | None:
        if account is not None:
            result = db.session.get(cls, (project.id, account.id))
            if not result and create:
                result = cls(project=project, participant=account)
                db.session.add(result)
            return result
        return None
