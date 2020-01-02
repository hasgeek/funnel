# -*- coding: utf-8 -*-

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr

from coaster.sqlalchemy import immutable

from . import db
from .membership import ImmutableMembershipMixin
from .proposal import Proposal

__all__ = ['ProposalMembership']


class ProposalMembership(ImmutableMembershipMixin, db.Model):
    """
    Users can be crew members of projects, with specified access rights.
    """

    __tablename__ = 'proposal_membership'

    # List of is_role columns in this model
    __data_columns__ = ('is_reviewer', 'is_speaker')

    __roles__ = {
        'all': {'read': {'user', 'is_reviewer', 'is_speaker', 'proposal'}},
        'editor': {'read': {'edit_url', 'delete_url'}},
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
    #: Speakers can edit and withdraw proposals
    is_speaker = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        args = list(super(cls, cls).__table_args__)
        args.append(
            db.CheckConstraint(
                'is_reviewer IS TRUE OR is_speaker IS TRUE',
                name='proposal_membership_has_role',
            )
        )
        return tuple(args)

    @property
    def edit_url(self):
        return self.url_for('edit', _external=True)

    @property
    def delete_url(self):
        return self.url_for('delete', _external=True)

    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = set()
        if self.is_reviewer:
            roles.add('reviewer')
        elif self.is_speaker:
            roles.add('speaker')
        return roles


# Project relationships: all crew, vs specific roles

Proposal.active_memberships = db.relationship(
    ProposalMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProposalMembership.proposal_id == Proposal.id, ProposalMembership.is_active
    ),
)

Proposal.active_reviewer_memberships = db.relationship(
    ProposalMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProposalMembership.proposal_id == Proposal.id,
        ProposalMembership.is_active,
        ProposalMembership.is_reviewer.is_(True),
    ),
)

Proposal.active_speaker_memberships = db.relationship(
    ProposalMembership,
    lazy='dynamic',
    primaryjoin=db.and_(
        ProposalMembership.proposal_id == Proposal.id,
        ProposalMembership.is_active,
        ProposalMembership.is_speaker.is_(True),
    ),
)

Proposal.crew = association_proxy('active_memberships', 'user')
Proposal.editors = association_proxy('active_reviewer_memberships', 'user')
Proposal.concierges = association_proxy('active_speaker_memberships', 'user')
