# -*- coding: utf-8 -*-

from baseframe import __
from coaster.sqlalchemy import StateManager, with_roles
from coaster.utils import LabeledEnum

from . import TimestampMixin, db
from .project import Project
from .user import User

__all__ = ['Rsvp', 'RSVP_STATUS']


class RSVP_STATUS(LabeledEnum):  # NOQA: N801
    # If you add any new state, you need to add a migration to modify the check constraint
    YES = ('Y', 'yes', __("Going"))
    NO = ('N', 'no', __("Not going"))
    MAYBE = ('M', 'maybe', __("Maybe"))
    AWAITING = ('A', 'awaiting', __("Awaiting"))
    __order__ = (YES, NO, MAYBE, AWAITING)
    # USER_CHOICES = {YES, NO, MAYBE}


class Rsvp(TimestampMixin, db.Model):
    __tablename__ = 'rsvp'
    project_id = db.Column(
        None, db.ForeignKey('project.id'), nullable=False, primary_key=True
    )
    project = db.relationship(
        Project,
        backref=db.backref('rsvps', cascade='all, delete-orphan', lazy='dynamic'),
    )
    user_id = db.Column(
        None, db.ForeignKey('user.id'), nullable=False, primary_key=True
    )
    user = with_roles(db.relationship(User), grants={'owner'})

    _state = db.Column(
        'state',
        db.CHAR(1),
        StateManager.check_constraint('state', RSVP_STATUS),
        default=RSVP_STATUS.AWAITING,
        nullable=False,
    )
    state = StateManager('_state', RSVP_STATUS, doc="RSVP answer")

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

    @classmethod
    def get_for(cls, project, user, create=False):
        if user:
            result = cls.query.get((project.id, user.id))
            if not result and create:
                result = cls(project=project, user=user)
                db.session.add(result)
            return result


def _project_rsvp_for(self, user, create=False):
    return Rsvp.get_for(self, user, create)


def _project_rsvps_with(self, status):
    return self.rsvps.filter_by(_state=status)


def _project_rsvp_counts(self):
    return dict(
        db.session.query(Rsvp._state, db.func.count(Rsvp._state))
        .filter(Rsvp.project == self)
        .group_by(Rsvp._state)
        .all()
    )


Project.rsvp_for = _project_rsvp_for
Project.rsvps_with = _project_rsvps_with
Project.rsvp_counts = _project_rsvp_counts
