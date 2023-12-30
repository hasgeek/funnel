"""Membership model for collaborators on a proposal (submission)."""

from __future__ import annotations

from typing import ClassVar

from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable, with_roles

from . import Mapped, Model, relationship, sa, sa_orm
from .membership_mixin import (
    FrozenAttributionProtoMixin,
    ImmutableUserMembershipMixin,
    ReorderMembershipProtoMixin,
)
from .proposal import Proposal

__all__ = ['ProposalMembership']


class ProposalMembership(  # type: ignore[misc]
    ImmutableUserMembershipMixin,
    FrozenAttributionProtoMixin,
    ReorderMembershipProtoMixin,
    Model,
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

    revoke_on_member_delete: ClassVar[bool] = False

    proposal_id: Mapped[int] = with_roles(
        sa_orm.mapped_column(
            sa.ForeignKey('proposal.id', ondelete='CASCADE'),
            default=None,
            nullable=False,
        ),
        read={'member', 'editor'},
    )

    proposal: Mapped[Proposal] = with_roles(
        relationship(back_populates='all_memberships'),
        read={'member', 'editor'},
        grants_via={None: {'editor'}},
    )
    parent_id: Mapped[int] = sa_orm.synonym('proposal_id')
    parent_id_column = 'proposal_id'
    parent: Mapped[Proposal] = sa_orm.synonym('proposal')

    #: Uncredited members are not listed in the main display, but can edit and may be
    #: listed in a details section. Uncredited memberships are for support roles such
    #: as copy editors.
    is_uncredited: Mapped[bool] = sa_orm.mapped_column(default=False)

    #: Optional label, indicating the member's role on the proposal
    label: Mapped[str | None] = immutable(
        sa_orm.mapped_column(
            sa.CheckConstraint("label <> ''", name='proposal_membership_label_check')
        )
    )

    @cached_property
    def offered_roles(self) -> set[str]:
        """Roles offered by this membership record."""
        # This method is not used. See the `Proposal.memberships` relationship below.
        return {'submitter', 'editor'}
