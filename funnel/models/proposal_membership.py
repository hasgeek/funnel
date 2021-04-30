from typing import Optional, Set

from werkzeug.utils import cached_property

from coaster.auth import current_auth
from coaster.sqlalchemy import immutable, with_roles

from . import db
from .helpers import reopen
from .membership_mixin import ImmutableUserMembershipMixin, ReorderMembershipMixin
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

    __roles__ = {'all': {'read': {'urls', 'user', 'seq', 'is_uncredited', 'label'}}}
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
        db.Column(
            None, db.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
        )
    )
    proposal = immutable(
        db.relationship(
            Proposal,
            backref=db.backref(
                'all_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        )
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
        # These grants are authoritative and used instead of `offered_roles` above
        grants_via={'user': {'submitter', 'editor'}},
    )

    @property
    def speaker(self) -> Optional[User]:
        """Return the first credited member on the proposal."""
        for membership in self.memberships:
            if not membership.is_uncredited:
                return membership.user
        return None

    @speaker.setter
    def speaker(self, value: Optional[User]):
        """Replace a member on a proposal."""
        credited_memberships = [m for m in self.memberships if not m.is_uncredited]
        if len(credited_memberships) > 1:
            raise ValueError("Too many speakers, don't know which to replace")

        # This is a hack to make the `speaker` property behave for legacy code. Modern
        # code should send in an explicit actor
        actor = current_auth.actor if current_auth and current_auth.actor else self.user

        if credited_memberships:
            if credited_memberships[0].user == value:
                # Existing speaker is the same as new speaker.
                # Nothing to do, just return
                return
            # There is an existing `speaker`. Revoke their membership
            credited_memberships[0].revoke(actor)

        # Add a membership. XXX: This does not append to the `self.memberships` list, so
        # reading the `speaker` property immediately after setting it will not return
        # the expected value. A database commit is necessary to refresh the list. This
        # poor behaviour is only tolerable because the `speaker` property is support for
        # legacy code pending upgrade
        db.session.add(ProposalMembership(proposal=self, user=value, granted_by=actor))


@reopen(User)
class __User:
    proposal_memberships = db.relationship(
        ProposalMembership,
        lazy='dynamic',
        foreign_keys=[ProposalMembership.user_id],
        viewonly=True,
    )
