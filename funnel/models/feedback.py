# -*- coding: utf-8 -*-

from . import db, BaseMixin
from .proposal import Proposal

__all__ = ['FEEDBACK_AUTH_TYPE', 'ProposalFeedback']


# --- Constants ---------------------------------------------------------------

class FEEDBACK_AUTH_TYPE:
    NOAUTH = 0
    HGAUTH = 1


# --- Models ------------------------------------------------------------------

class ProposalFeedback(BaseMixin, db.Model):
    __tablename__ = 'proposal_feedback'
    #: Proposal that we're submitting feedback on
    proposal_id = db.Column(None, db.ForeignKey('proposal.id'), nullable=False)
    proposal = db.relationship(Proposal)
    #: Authentication type (authenticated or not)
    auth_type = db.Column(db.Integer, nullable=False)
    #: Type of identifier for the user
    id_type = db.Column(db.Unicode(80), nullable=False)
    #: User id (of the given type)
    userid = db.Column(db.Unicode(80), nullable=False)
    #: Minimum scale for feedback (x in x-y)
    min_scale = db.Column(db.Integer, nullable=False)
    #: Maximum scale for feedback (y in x-y)
    max_scale = db.Column(db.Integer, nullable=False)
    #: Feedback on the content of the proposal
    content = db.Column(db.Integer, nullable=True)
    #: Feedback on the presentation of the proposal
    presentation = db.Column(db.Integer, nullable=True)

    __table_args__ = (db.UniqueConstraint('proposal_id', 'auth_type', 'id_type', 'userid'),)
