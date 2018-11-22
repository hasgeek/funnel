# -*- coding: utf-8 -*-

from coaster.utils import LabeledEnum
from coaster.sqlalchemy import StateManager
from baseframe import __
from . import db, TimestampMixin
from .project import Project
from .user import User

__all__ = ['Rsvp', 'RSVP_STATUS']


class RSVP_STATUS(LabeledEnum):
    # If you add any new state, you need to add a migration to modify the check constraint
    Y = ('Y', 'yes', __("Yes"))
    N = ('N', 'no', __("No"))
    M = ('M', 'maybe', __("Maybe"))
    A = ('A', 'awaiting', __("Awaiting"))
    # To avoid interfering with LabeledEnum, the following should use a list, not a tuple,
    # and should contain actual status values, not Python objects
    USER_CHOICES = ['Y', 'N', 'M']


class Rsvp(TimestampMixin, db.Model):
    __tablename__ = 'rsvp'
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False, primary_key=True)
    project = db.relationship(Project,
        backref=db.backref('rsvps', cascade='all, delete-orphan', lazy='dynamic'))
    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    user = db.relationship(User)

    _state = db.Column('state', db.CHAR(1), StateManager.check_constraint('state', RSVP_STATUS),
        default=RSVP_STATUS.A, nullable=False)
    state = StateManager('_state', RSVP_STATUS, doc="RSVP answer")

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
    return dict(db.session.query(Rsvp._state, db.func.count(Rsvp._state)).filter(
        Rsvp.project == self).group_by(Rsvp._state).all())


Project.rsvp_for = _project_rsvp_for
Project.rsvps_with = _project_rsvps_with
Project.rsvp_counts = _project_rsvp_counts
