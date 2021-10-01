from __future__ import annotations

from typing import List, Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin, ReorderMembershipMixin
from .project import Project
from .proposal import Proposal
from .user import User

__all__ = ['ProposalMembership']


class ProposalMembership(
    ReorderMembershipMixin, ImmutableUserMembershipMixin, db.Model
):
    """Users can be presenters or reviewers on proposals."""

    __tablename__ = 'proposal_membership'

    # List of is_role columns in this model
    __data_columns__ = ('seq', 'is_uncredited', 'label')

    __roles__ = {
        'all': {
            'read': {'urls', 'user', 'seq', 'is_uncredited', 'label'},
            'call': {'url_for'},
        },
        'editor': {
            'call': {'reorder_item', 'reorder_before', 'reorder_after'},
        },
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'seq',
            'is_uncredited',
            'label',
            'user',
            'proposal',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'seq',
            'is_uncredited',
            'label',
            'user',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'seq',
            'is_uncredited',
            'label',
        },
    }

    proposal_id = immutable(
        with_roles(
            db.Column(
                None, db.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
            ),
            read={'subject', 'editor'},
        ),
    )
    proposal = immutable(
        with_roles(
            db.relationship(
                Proposal,
                backref=db.backref(
                    'all_memberships',
                    lazy='dynamic',
                    cascade='all',
                    passive_deletes=True,
                ),
            ),
            read={'subject', 'editor'},
            grants_via={None: {'editor'}},
        ),
    )
    parent = db.synonym('proposal')
    parent_id = db.synonym('proposal_id')

    #: Uncredited members are not listed in the main display, but can edit and may be
    #: listed in a details section. Uncredited memberships are for support roles such
    #: as copy editors.
    is_uncredited = db.Column(db.Boolean, nullable=False, default=False)

    #: Optional label, indicating the member's role on the proposal
    label = immutable(
        db.Column(
            db.Unicode,
            db.CheckConstraint(
                db.column('label') != '', name='proposal_membership_label_check'
            ),
            nullable=True,
        )
    )

    @cached_property
    def offered_roles(self) -> Set[str]:
        """Roles offered by this membership record."""
        # This method is not used. See the `Proposal.memberships` relationship below.
        return {'submitter', 'editor'}


# Project relationships
@reopen(Proposal)
class __Proposal:
    user: User

    # This relationship does not use `lazy='dynamic'` because it is expected to contain
    # <2 records on average, and won't exceed 50 in the most extreme cases
    memberships = with_roles(
        db.relationship(
            ProposalMembership,
            primaryjoin=db.and_(
                ProposalMembership.proposal_id == Proposal.id,
                ProposalMembership.is_active,
            ),
            order_by=ProposalMembership.seq,
            viewonly=True,
        ),
        read={'all'},
        # These grants are authoritative and used instead of `offered_roles` above
        grants_via={'user': {'submitter', 'editor'}},
    )

    @with_roles(call={'project_editor'})
    def transfer_to(self, users: List[User], actor: User):
        """Replace the members on a proposal."""
        userset = set(users)  # Make a copy to work on
        for member in self.memberships:
            if member.user not in userset:
                # Revoke this membership
                member.revoke(actor=actor)
            else:
                # Don't need to modify this membership
                userset.remove(member.user)

        # Add a membership. XXX: This does not append to the `self.memberships` list, so
        # reading the `first_user` property immediately after setting it will not return
        # the expected value. A database commit is necessary to refresh the list. This
        # poor behaviour is only tolerable because the `first_user` property is support
        # for legacy code pending upgrade
        for user in userset:
            db.session.add(
                ProposalMembership(proposal=self, user=user, granted_by=actor)
            )

    @property
    def first_user(self) -> User:
        """Return the first credited member on the proposal, or creator if none."""
        for membership in self.memberships:
            if not membership.is_uncredited:
                return membership.user
        return self.user


@reopen(User)
class __User:
    all_proposal_memberships = db.relationship(
        ProposalMembership,
        lazy='dynamic',
        foreign_keys=[ProposalMembership.user_id],
        viewonly=True,
    )

    proposal_memberships = db.relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            ProposalMembership.user_id == User.id,
            ProposalMembership.is_active,
        ),
        viewonly=True,
    )

    proposals = DynamicAssociationProxy('proposal_memberships', 'proposal')

    @property
    def public_proposal_memberships(self):
        """Query for all proposal memberships to proposals that are public."""
        return (
            self.proposal_memberships.join(Proposal, ProposalMembership.proposal)
            .join(Project, Proposal.project)
            .filter()
        )

    public_proposals = DynamicAssociationProxy(
        'public_proposal_memberships', 'proposal'
    )
