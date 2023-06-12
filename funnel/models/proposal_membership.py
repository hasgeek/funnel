"""Membership model for collaborators on a proposal (submission)."""

from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import DynamicMapped, Mapped, Model, relationship, sa
from .helpers import reopen
from .membership_mixin import (
    FrozenAttributionMixin,
    ImmutableUserMembershipMixin,
    ReorderMembershipMixin,
)
from .project import Project
from .proposal import Proposal
from .user import User

__all__ = ['ProposalMembership']


class ProposalMembership(  # type: ignore[misc]
    FrozenAttributionMixin, ReorderMembershipMixin, ImmutableUserMembershipMixin, Model
):
    """Users can be presenters or reviewers on proposals."""

    __tablename__ = 'proposal_membership'
    __allow_unmapped__ = True

    # List of data columns in this model
    __data_columns__ = ('seq', 'is_uncredited', 'label', 'title')

    __roles__ = {
        'all': {
            'read': {'is_uncredited', 'label', 'seq', 'title', 'urls', 'user'},
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
            'user',
            'uuid_b58',
        },
        'without_parent': {
            'is_uncredited',
            'label',
            'offered_roles',
            'seq',
            'title',
            'urls',
            'user',
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

    revoke_on_subject_delete = False

    proposal_id: Mapped[int] = with_roles(
        sa.orm.mapped_column(
            sa.Integer,
            sa.ForeignKey('proposal.id', ondelete='CASCADE'),
            nullable=False,
        ),
        read={'subject', 'editor'},
    )

    proposal: Mapped[Proposal] = with_roles(
        relationship(
            Proposal,
            backref=sa.orm.backref(
                'all_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        ),
        read={'subject', 'editor'},
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
        grants_via={'user': {'submitter', 'editor'}},
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
    # pylint: disable=invalid-unary-operand-type

    all_proposal_memberships: DynamicMapped[ProposalMembership] = relationship(
        ProposalMembership,
        lazy='dynamic',
        foreign_keys=[ProposalMembership.user_id],
        viewonly=True,
    )

    noninvite_proposal_memberships: DynamicMapped[ProposalMembership] = relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalMembership.user_id == User.id,
            ~ProposalMembership.is_invite,
        ),
        viewonly=True,
    )

    proposal_memberships: DynamicMapped[ProposalMembership] = relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
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
            .filter(
                ProposalMembership.is_uncredited.is_(False),
                # TODO: Include proposal state filter (pending proposal workflow fix)
            )
        )

    public_proposals = DynamicAssociationProxy(
        'public_proposal_memberships', 'proposal'
    )


User.__active_membership_attrs__.add('proposal_memberships')
User.__noninvite_membership_attrs__.add('noninvite_proposal_memberships')
