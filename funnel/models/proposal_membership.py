"""Membership model for collaborators on a proposal (submission)."""

from __future__ import annotations

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import DynamicMapped, Mapped, Model, backref, relationship, sa
from .account import Account
from .helpers import reopen
from .membership_mixin import (
    FrozenAttributionMixin,
    ImmutableUserMembershipMixin,
    ReorderMembershipMixin,
)
from .project import Project
from .proposal import Proposal

__all__ = ['ProposalMembership']


class ProposalMembership(  # type: ignore[misc]
    FrozenAttributionMixin, ReorderMembershipMixin, ImmutableUserMembershipMixin, Model
):
    """Users can be presenters or reviewers on proposals."""

    __tablename__ = 'proposal_membership'

    # List of data columns in this model
    __data_columns__ = ('seq', 'is_uncredited', 'label', 'title')

    __roles__ = {
        'all': {
            'read': {'is_uncredited', 'label', 'seq', 'title', 'urls', 'member'},
            'call': {'url_for'},
        },
        'editor': {
            'call': {'reorder_item', 'reorder_before', 'reorder_after'},
        },
    }
    __datasets__ = {
        'primary': {
            'is_uncredited',
            'label',
            'offered_roles',
            'proposal',
            'seq',
            'title',
            'urls',
            'member',
            'uuid_b58',
        },
        'without_parent': {
            'is_uncredited',
            'label',
            'offered_roles',
            'seq',
            'title',
            'urls',
            'member',
            'uuid_b58',
        },
        'related': {
            'is_uncredited',
            'label',
            'offered_roles',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
    }

    revoke_on_member_delete = False

    proposal_id: Mapped[int] = with_roles(
        sa.orm.mapped_column(
            sa.Integer,
            sa.ForeignKey('proposal.id', ondelete='CASCADE'),
            nullable=False,
        ),
        read={'member', 'editor'},
    )

    proposal: Mapped[Proposal] = with_roles(
        relationship(
            Proposal,
            backref=backref(
                'all_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        ),
        read={'member', 'editor'},
        grants_via={None: {'editor'}},
    )
    parent_id: Mapped[int] = sa.orm.synonym('proposal_id')
    parent_id_column = 'proposal_id'
    parent: Mapped[Proposal] = sa.orm.synonym('proposal')

    #: Uncredited members are not listed in the main display, but can edit and may be
    #: listed in a details section. Uncredited memberships are for support roles such
    #: as copy editors.
    is_uncredited = sa.orm.mapped_column(sa.Boolean, nullable=False, default=False)

    #: Optional label, indicating the member's role on the proposal
    label = immutable(
        sa.orm.mapped_column(
            sa.Unicode,
            sa.CheckConstraint("label <> ''", name='proposal_membership_label_check'),
            nullable=True,
        )
    )

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered by this membership record."""
        # This method is not used. See the `Proposal.memberships` relationship below.
        return {'submitter', 'editor'}


# Project relationships
@reopen(Proposal)
class __Proposal:
    created_by: Account

    # This relationship does not use `lazy='dynamic'` because it is expected to contain
    # <2 records on average, and won't exceed 50 in the most extreme cases
    memberships = with_roles(
        relationship(
            ProposalMembership,
            primaryjoin=sa.and_(
                ProposalMembership.proposal_id == Proposal.id,
                ProposalMembership.is_active,
            ),
            order_by=ProposalMembership.seq,
            viewonly=True,
        ),
        read={'all'},
        # These grants are authoritative and used instead of `offered_roles` above
        grants_via={'member': {'submitter', 'editor'}},
    )

    @property
    def first_user(self) -> Account:
        """Return the first credited member on the proposal, or creator if none."""
        for membership in self.memberships:
            if not membership.is_uncredited:
                return membership.member
        return self.created_by


@reopen(Account)
class __Account:
    # pylint: disable=invalid-unary-operand-type

    all_proposal_memberships: DynamicMapped[ProposalMembership] = relationship(
        ProposalMembership,
        lazy='dynamic',
        foreign_keys=[ProposalMembership.member_id],
        viewonly=True,
    )

    noninvite_proposal_memberships: DynamicMapped[ProposalMembership] = relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalMembership.member_id == Account.id,
            ~ProposalMembership.is_invite,
        ),
        viewonly=True,
    )

    proposal_memberships: DynamicMapped[ProposalMembership] = relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalMembership.member_id == Account.id,
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
            .filter(
                ProposalMembership.is_uncredited.is_(False),
                # TODO: Include proposal state filter (pending proposal workflow fix)
            )
        )

    public_proposals = DynamicAssociationProxy(
        'public_proposal_memberships', 'proposal'
    )


Account.__active_membership_attrs__.add('proposal_memberships')
Account.__noninvite_membership_attrs__.add('noninvite_proposal_memberships')
