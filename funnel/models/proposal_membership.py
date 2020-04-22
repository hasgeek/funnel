# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declared_attr

from coaster.sqlalchemy import DynamicAssociationProxy, immutable

from . import db
from .membership import ImmutableMembershipMixin
from .proposal import Proposal

__all__ = ['ProposalMembership']


class ProposalMembership(ImmutableMembershipMixin, db.Model):
    """
    Users can be presenters or reviewers on proposals.
    """

    __tablename__ = 'proposal_membership'

    # List of is_role columns in this model
    __data_columns__ = ('is_reviewer', 'is_presenter')

    __roles__ = {
        'all': {'read': {'urls', 'user', 'is_reviewer', 'is_presenter', 'proposal'}}
    }

    proposal_id = immutable(
        db.Column(
            None, db.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
        )
    )
    proposal = immutable(
        db.relationship(
            Proposal,
            backref=db.backref(
                'memberships',
                lazy='dynamic',
                cascade='all, delete-orphan',
                passive_deletes=True,
            ),
        )
    )
    parent = immutable(db.synonym('proposal'))
    parent_id = immutable(db.synonym('proposal_id'))

    # Proposal roles (at least one must be True):

    #: Reviewers can change state of proposal
    is_reviewer = db.Column(db.Boolean, nullable=False, default=False)
    #: Presenters can edit and withdraw proposals
    is_presenter = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        args = list(super().__table_args__)
        args.append(
            db.CheckConstraint(
                db.or_(cls.is_reviewer.is_(True), cls.is_presenter.is_(True)),
                name='proposal_membership_has_role',
            )
        )
        return tuple(args)

    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = set()
        if self.is_reviewer:
            roles.add('reviewer')
        elif self.is_speaker:
            roles.add('presenter')
        return roles


# Project relationships: all crew, vs specific roles

Proposal.active_memberships = db.relationship(
    ProposalMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProposalMembership.proposal_id == Proposal.id, ProposalMembership.is_active
    ),
    viewonly=True,
)

Proposal.active_reviewer_memberships = db.relationship(
    ProposalMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProposalMembership.proposal_id == Proposal.id,
        ProposalMembership.is_active,
        ProposalMembership.is_reviewer.is_(True),
    ),
    viewonly=True,
)

Proposal.active_presenter_memberships = db.relationship(
    ProposalMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProposalMembership.proposal_id == Proposal.id,
        ProposalMembership.is_active,
        ProposalMembership.is_presenter.is_(True),
    ),
    viewonly=True,
)

Proposal.members = DynamicAssociationProxy('active_memberships', 'user')
Proposal.reviewers = DynamicAssociationProxy('active_reviewer_memberships', 'user')
Proposal.presenters = DynamicAssociationProxy('active_presenters_memberships', 'user')
