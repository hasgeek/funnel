"""Legacy project registration model, storing RSVP states (Y/N/M/A)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple, Union, cast, overload
from typing_extensions import Literal

from flask import current_app
from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from ..typing import OptionalMigratedTables
from . import Mapped, Model, NoIdMixin, UuidMixin, db, relationship, sa, types
from .helpers import reopen
from .project import Project
from .project_membership import project_child_role_map
from .user import User, UserEmail, UserEmailClaim, UserPhone

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
    __allow_unmapped__ = True
    project_id = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id'), nullable=False, primary_key=True
    )
    project = with_roles(
        relationship(
            Project, backref=sa.orm.backref('rsvps', cascade='all', lazy='dynamic')
        ),
        read={'owner', 'project_promoter'},
        grants_via={None: project_child_role_map},
        datasets={'primary'},
    )
    user_id = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('user.id'), nullable=False, primary_key=True
    )
    user = with_roles(
        relationship(
            User, backref=sa.orm.backref('rsvps', cascade='all', lazy='dynamic')
        ),
        read={'owner', 'project_promoter'},
        grants={'owner'},
        datasets={'primary', 'without_parent'},
    )
    form: Mapped[Optional[types.jsonb]] = with_roles(
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

    @with_roles(call={'owner', 'project_promoter'})
    def user_email(self) -> Optional[UserEmail]:
        """User's preferred email address for this registration."""
        return self.user.transport_for_email(self.project.profile)

    @with_roles(call={'owner', 'project_promoter'})
    def user_phone(self) -> Optional[UserEmail]:
        """User's preferred phone number for this registration."""
        return self.user.transport_for_sms(self.project.profile)

    @with_roles(call={'owner', 'project_promoter'})
    def best_contact(
        self,
    ) -> Tuple[Union[UserEmail, UserEmailClaim, UserPhone, None], str]:
        email = self.user_email()
        if email:
            return email, 'e'
        phone = self.user_phone()
        if phone:
            return phone, 'p'
        if self.user.emailclaims:
            return self.user.emailclaims[0], 'ec'
        return None, ''

    @classmethod
    def migrate_user(  # type: ignore[return]
        cls, old_user: User, new_user: User
    ) -> OptionalMigratedTables:
        """Migrate one user account to another when merging user accounts."""
        project_ids = {rsvp.project_id for rsvp in new_user.rsvps}
        for rsvp in old_user.rsvps:
            if rsvp.project_id not in project_ids:
                rsvp.user = new_user
            else:
                current_app.logger.warning(
                    "Discarding conflicting RSVP (%s) from %r on %r",
                    rsvp._state,  # pylint: disable=protected-access
                    old_user,
                    rsvp.project,
                )
                db.session.delete(rsvp)

    @overload
    @classmethod
    def get_for(cls, project: Project, user: User, create: Literal[True]) -> Rsvp:
        ...

    @overload
    @classmethod
    def get_for(
        cls, project: Project, user: User, create: Literal[False]
    ) -> Optional[Rsvp]:
        ...

    @overload
    @classmethod
    def get_for(
        cls, project: Project, user: Optional[User], create=False
    ) -> Optional[Rsvp]:
        ...

    @classmethod
    def get_for(
        cls, project: Project, user: Optional[User], create=False
    ) -> Optional[Rsvp]:
        if user is not None:
            result = cls.query.get((project.id, user.id))
            if not result and create:
                result = cls(project=project, user=user)
                db.session.add(result)
            return result
        return None


@reopen(Project)
class __Project:
    @property
    def active_rsvps(self):
        return self.rsvps.join(User).filter(Rsvp.state.YES, User.state.ACTIVE)

    with_roles(
        active_rsvps, grants_via={Rsvp.user: {'participant', 'project_participant'}}
    )

    @overload
    def rsvp_for(self, user: User, create: Literal[True]) -> Rsvp:
        ...

    @overload
    def rsvp_for(self, user: Optional[User], create: Literal[False]) -> Optional[Rsvp]:
        ...

    def rsvp_for(self, user: Optional[User], create=False) -> Optional[Rsvp]:
        return Rsvp.get_for(cast(Project, self), user, create)

    def rsvps_with(self, status: str):
        return (
            cast(Project, self)
            .rsvps.join(User)
            .filter(
                User.state.ACTIVE,
                Rsvp._state == status,  # pylint: disable=protected-access
            )
        )

    def rsvp_counts(self) -> Dict[str, int]:
        return dict(
            db.session.query(
                Rsvp._state,  # pylint: disable=protected-access
                sa.func.count(Rsvp._state),  # pylint: disable=protected-access
            )
            .join(User)
            .filter(User.state.ACTIVE, Rsvp.project == self)
            .group_by(Rsvp._state)  # pylint: disable=protected-access
            .all()
        )

    @cached_property
    def rsvp_count_going(self) -> int:
        return (
            cast(Project, self)
            .rsvps.join(User)
            .filter(User.state.ACTIVE, Rsvp.state.YES)
            .count()
        )
