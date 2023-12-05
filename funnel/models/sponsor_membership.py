"""Models for sponsors of a project or proposal (submission)."""

from __future__ import annotations

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import DynamicMapped, Mapped, Model, backref, db, relationship, sa
from .account import Account
from .helpers import reopen
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

    revoke_on_member_delete = False

    project_id: Mapped[int] = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False
    )
    project: Mapped[Project] = relationship(
        Project,
        backref=backref(
            'all_sponsor_memberships',
            lazy='dynamic',
            cascade='all',
            passive_deletes=True,
        ),
    )
    parent_id: Mapped[int] = sa.orm.synonym('project_id')
    parent_id_column = 'project_id'
    parent: Mapped[Project] = sa.orm.synonym('project')

    #: Is this sponsor being promoted for commercial reasons? Projects may have a legal
    #: obligation to reveal this. This column records a declaration from the project.
    is_promoted = immutable(sa.orm.mapped_column(sa.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(
        sa.orm.mapped_column(
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


@reopen(Project)
class __Project:
    sponsor_memberships: DynamicMapped[ProjectSponsorMembership] = with_roles(
        relationship(
            ProjectSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProjectSponsorMembership.project_id == Project.id,
                ProjectSponsorMembership.is_active,
            ),
            order_by=ProjectSponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self) -> bool:
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy('sponsor_memberships', 'member')


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

    revoke_on_member_delete = False

    proposal_id: Mapped[int] = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
    )
    proposal: Mapped[Proposal] = relationship(
        Proposal,
        backref=backref(
            'all_sponsor_memberships',
            lazy='dynamic',
            cascade='all',
            passive_deletes=True,
        ),
    )
    parent_id: Mapped[int] = sa.orm.synonym('proposal_id')
    parent_id_column = 'proposal_id'
    parent: Mapped[Proposal] = sa.orm.synonym('proposal')

    #: Is this sponsor being promoted for commercial reasons? Proposals may have a legal
    #: obligation to reveal this. This column records a declaration from the proposal.
    is_promoted = immutable(sa.orm.mapped_column(sa.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(
        sa.orm.mapped_column(
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


@reopen(Proposal)
class __Proposal:
    sponsor_memberships: DynamicMapped[ProposalSponsorMembership] = with_roles(
        relationship(
            ProposalSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProposalSponsorMembership.proposal_id == Proposal.id,
                ProposalSponsorMembership.is_active,
            ),
            order_by=ProposalSponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self) -> bool:
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy('sponsor_memberships', 'member')


@reopen(Account)
class __Account:
    # pylint: disable=invalid-unary-operand-type
    noninvite_project_sponsor_memberships: DynamicMapped[
        ProjectSponsorMembership
    ] = relationship(
        ProjectSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProjectSponsorMembership.member_id == Account.id,
            ~ProjectSponsorMembership.is_invite,
        ),
        order_by=ProjectSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    project_sponsor_memberships: DynamicMapped[ProjectSponsorMembership] = relationship(
        ProjectSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProjectSponsorMembership.member_id == Account.id,
            ProjectSponsorMembership.is_active,
        ),
        order_by=ProjectSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    project_sponsor_membership_invites: DynamicMapped[
        ProjectSponsorMembership
    ] = with_roles(
        relationship(
            ProjectSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProjectSponsorMembership.member_id == Account.id,
                ProjectSponsorMembership.is_invite,
                ProjectSponsorMembership.revoked_at.is_(None),
            ),
            order_by=ProjectSponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'admin'},
    )

    noninvite_proposal_sponsor_memberships: DynamicMapped[
        ProposalSponsorMembership
    ] = relationship(
        ProposalSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalSponsorMembership.member_id == Account.id,
            ~ProposalSponsorMembership.is_invite,
        ),
        order_by=ProposalSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    proposal_sponsor_memberships: DynamicMapped[
        ProposalSponsorMembership
    ] = relationship(
        ProposalSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalSponsorMembership.member_id == Account.id,
            ProposalSponsorMembership.is_active,
        ),
        order_by=ProposalSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    proposal_sponsor_membership_invites: DynamicMapped[
        ProposalSponsorMembership
    ] = with_roles(
        relationship(
            ProposalSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProposalSponsorMembership.member_id == Account.id,
                ProposalSponsorMembership.is_invite,
                ProposalSponsorMembership.revoked_at.is_(None),
            ),
            order_by=ProposalSponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'admin'},
    )

    sponsored_projects = DynamicAssociationProxy(
        'project_sponsor_memberships', 'project'
    )

    sponsored_proposals = DynamicAssociationProxy(
        'proposal_sponsor_memberships', 'proposal'
    )


Account.__active_membership_attrs__.update(
    {'project_sponsor_memberships', 'proposal_sponsor_memberships'}
)
Account.__noninvite_membership_attrs__.update(
    {'noninvite_project_sponsor_memberships', 'noninvite_proposal_sponsor_memberships'}
)
