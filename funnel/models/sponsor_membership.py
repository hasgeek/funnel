"""Models for sponsors of a project or proposal (submission)."""

from __future__ import annotations

from typing import ClassVar

from werkzeug.utils import cached_property

from coaster.sqlalchemy import immutable

from . import Mapped, Model, relationship, sa, sa_orm
from .membership_mixin import (
    FrozenAttributionProtoMixin,
    ImmutableUserMembershipMixin,
    ReorderMembershipProtoMixin,
)
from .project import Project
from .proposal import Proposal

__all__ = ['ProjectSponsorMembership', 'ProposalSponsorMembership']


class ProjectSponsorMembership(  # type: ignore[misc]
    ImmutableUserMembershipMixin,
    FrozenAttributionProtoMixin,
    ReorderMembershipProtoMixin,
    Model,
):
    """Sponsor of a project."""

    __tablename__ = 'project_sponsor_membership'

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label', 'title')

    __roles__ = {
        'all': {
            'read': {
                'is_promoted',
                'label',
                'member',
                'project',
                'seq',
                'title',
                'urls',
            },
            'call': {'url_for'},
        }
    }
    __datasets__ = {
        'primary': {
            'is_promoted',
            'label',
            'offered_roles',
            'member',
            'project',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
        'without_parent': {
            'is_promoted',
            'label',
            'offered_roles',
            'member',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
        'related': {
            'is_promoted',
            'label',
            'offered_roles',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
    }

    revoke_on_member_delete: ClassVar[bool] = False

    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False
    )
    project: Mapped[Project] = relationship(back_populates='all_sponsor_memberships')
    parent_id: Mapped[int] = sa_orm.synonym('project_id')
    parent_id_column = 'project_id'
    parent: Mapped[Project] = sa_orm.synonym('project')

    #: Is this sponsor being promoted for commercial reasons? Projects may have a legal
    #: obligation to reveal this. This column records a declaration from the project.
    is_promoted: Mapped[bool] = immutable(
        sa_orm.mapped_column(sa.Boolean, nullable=False)
    )

    #: Optional label, indicating the type of sponsor
    label: Mapped[str | None] = immutable(
        sa_orm.mapped_column(
            sa.Unicode,
            sa.CheckConstraint(
                "label <> ''", name='project_sponsor_membership_label_check'
            ),
            nullable=True,
        )
    )

    # This model does not offer a large text field for promotional messages, since
    # revision control on such a field is a distinct problem from membership
    # revisioning. The planned Page model can be used instead, with this model getting
    # a page id reference column whenever that model is ready.

    @cached_property
    def offered_roles(self) -> set[str]:
        """Return empty set as this membership does not offer any roles on Project."""
        return set()


# FIXME: Replace this with existing proposal collaborator as they're now both related
# to "account"
class ProposalSponsorMembership(  # type: ignore[misc]
    FrozenAttributionProtoMixin,
    ReorderMembershipProtoMixin,
    ImmutableUserMembershipMixin,
    Model,
):
    """Sponsor of a proposal."""

    __tablename__ = 'proposal_sponsor_membership'

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label', 'title')

    __roles__ = {
        'all': {
            'read': {
                'is_promoted',
                'label',
                'member',
                'proposal',
                'seq',
                'title',
                'urls',
            },
            'call': {'url_for'},
        }
    }
    __datasets__ = {
        'primary': {
            'is_promoted',
            'label',
            'offered_roles',
            'member',
            'proposal',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
        'without_parent': {
            'is_promoted',
            'label',
            'offered_roles',
            'member',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
        'related': {
            'is_promoted',
            'label',
            'offered_roles',
            'seq',
            'title',
            'urls',
            'uuid_b58',
        },
    }

    revoke_on_member_delete: ClassVar[bool] = False

    proposal_id: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
    )
    proposal: Mapped[Proposal] = relationship(back_populates='all_sponsor_memberships')
    parent_id: Mapped[int] = sa_orm.synonym('proposal_id')
    parent_id_column = 'proposal_id'
    parent: Mapped[Proposal] = sa_orm.synonym('proposal')

    #: Is this sponsor being promoted for commercial reasons? Proposals may have a legal
    #: obligation to reveal this. This column records a declaration from the proposal.
    is_promoted: Mapped[bool] = immutable(
        sa_orm.mapped_column(sa.Boolean, nullable=False)
    )

    #: Optional label, indicating the type of sponsor
    label: Mapped[str | None] = immutable(
        sa_orm.mapped_column(
            sa.Unicode,
            sa.CheckConstraint(
                "label <> ''", name='proposal_sponsor_membership_label_check'
            ),
            nullable=True,
        )
    )

    @cached_property
    def offered_roles(self) -> set[str]:
        """Return empty set as this membership does not offer any roles on Proposal."""
        return set()
