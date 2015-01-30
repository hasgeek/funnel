
from . import db, TimestampMixin
from coaster.utils import LabeledEnum
from baseframe import __

__all__ = ['RSVP', 'RSVP_ACTION']


class RSVP_ACTION(LabeledEnum):
    RSVP_Y = ('Y', {'label': "I'm going", 'category': 'primary', 'order': 1})
    RSVP_N = ('N', {'label': 'Not going', 'category': 'danger', 'order': 2})
    RSVP_M = ('M', {'label': 'Maybe', 'category': 'default', 'order': 3})


class RSVP(TimestampMixin, db.Model):
    """Captures an RSVP from the user for a proposal space"""
    __tablename__ = 'rsvp'
    __table_args__ = (db.UniqueConstraint('user_id', 'proposal_space_id'),)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    rsvp_action = db.Column(db.Enum(*RSVP_ACTION.keys(), name='rsvp_action'), default=RSVP_ACTION)

    def __init__(self, **kwargs):
        super(RSVP, self).__init__(**kwargs)
