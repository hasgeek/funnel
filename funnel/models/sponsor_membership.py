"""Models for sponsors of a project or proposal (submission)."""

from __future__ import annotations

from typing import Set
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import Mapped, db, sa
from .account import Account
from .helpers import reopen
from .membership_mixin import (
    FrozenAttributionMixin,
    ImmutableUserMembershipMixin,
    ReorderMembershipMixin,
)
from .project import Project
from .proposal import Proposal

__all__ = ['ProjectSponsorMembership', 'ProposalSponsorMembership']


class ProjectSponsorMembership(  # type: ignore[misc]
    FrozenAttributionMixin,
    ReorderMembershipMixin,
    ImmutableUserMembershipMixin,
    db.Model,  # type: ignore[name-defined]
):
    """Sponsor of a project."""

    __tablename__ = 'project_sponsor_membership'
    __allow_unmapped__ = True

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label', 'title')

    __roles__ = {
        'all': {
            'read': {
                'is_promoted',
                'label',
                'profile',
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
            'profile',
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
            'profile',
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

    revoke_on_subject_delete = False

    project_id: Mapped[int] = sa.Column(
        sa.Integer, sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False
    )
    project: Mapped[Project] = sa.orm.relationship(
        Project,
        backref=sa.orm.backref(
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
    is_promoted = immutable(sa.Column(sa.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(
        sa.Column(
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
    def offered_roles(self) -> Set[str]:
        """Return empty set as this membership does not offer any roles on Project."""
        return set()


@reopen(Project)
class __Project:
    sponsor_memberships = with_roles(
        sa.orm.relationship(
            ProjectSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProjectSponsorMembership.project_id == Project.id,
                ProjectSponsorMembership.is_active,  # type: ignore[arg-type]
            ),
            order_by=ProjectSponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self):
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy('sponsor_memberships', 'profile')


# FIXME: Replace this with existing proposal collaborator as they're now both related
# to "account"
class ProposalSponsorMembership(  # type: ignore[misc]
    FrozenAttributionMixin,
    ReorderMembershipMixin,
    ImmutableUserMembershipMixin,
    db.Model,  # type: ignore[name-defined]
):
    """Sponsor of a proposal."""

    __tablename__ = 'proposal_sponsor_membership'
    __allow_unmapped__ = True

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label', 'title')

    __roles__ = {
        'all': {
            'read': {
                'is_promoted',
                'label',
                'profile',
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
            'profile',
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
            'profile',
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

    revoke_on_subject_delete = False

    proposal_id: Mapped[int] = sa.Column(
        sa.Integer, sa.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
    )
    proposal: Mapped[Proposal] = sa.orm.relationship(
        Proposal,
        backref=sa.orm.backref(
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
    is_promoted = immutable(sa.Column(sa.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(
        sa.Column(
            sa.Unicode,
            sa.CheckConstraint(
                "label <> ''", name='proposal_sponsor_membership_label_check'
            ),
            nullable=True,
        )
    )

    @cached_property
    def offered_roles(self) -> Set[str]:
        """Return empty set as this membership does not offer any roles on Proposal."""
        return set()


@reopen(Proposal)
class __Proposal:
    sponsor_memberships = with_roles(
        sa.orm.relationship(
            ProposalSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProposalSponsorMembership.proposal_id == Proposal.id,
                ProposalSponsorMembership.is_active,  # type: ignore[arg-type]
            ),
            order_by=ProposalSponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self):
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy('sponsor_memberships', 'profile')


@reopen(Account)
class __Account:
    # pylint: disable=invalid-unary-operand-type
    noninvite_project_sponsor_memberships = sa.orm.relationship(
        ProjectSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProjectSponsorMembership.subject_id == Account.id,
            ~ProjectSponsorMembership.is_invite,  # type: ignore[operator]
        ),
        order_by=ProjectSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    project_sponsor_memberships = sa.orm.relationship(
        ProjectSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProjectSponsorMembership.subject_id == Account.id,
            ProjectSponsorMembership.is_active,  # type: ignore[arg-type]
        ),
        order_by=ProjectSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    project_sponsor_membership_invites = with_roles(
        sa.orm.relationship(
            ProjectSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProjectSponsorMembership.subject_id == Account.id,
                ProjectSponsorMembership.is_invite,  # type: ignore[arg-type]
                ProjectSponsorMembership.revoked_at.is_(None),  # type: ignore[has-type]
            ),
            order_by=ProjectSponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'admin'},
    )

    noninvite_proposal_sponsor_memberships = sa.orm.relationship(
        ProposalSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalSponsorMembership.subject_id == Account.id,
            ~ProposalSponsorMembership.is_invite,  # type: ignore[operator]
        ),
        order_by=ProposalSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    proposal_sponsor_memberships = sa.orm.relationship(
        ProposalSponsorMembership,
        lazy='dynamic',
        primaryjoin=sa.and_(
            ProposalSponsorMembership.subject_id == Account.id,
            ProposalSponsorMembership.is_active,  # type: ignore[arg-type]
        ),
        order_by=ProposalSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    proposal_sponsor_membership_invites = with_roles(
        sa.orm.relationship(
            ProposalSponsorMembership,
            lazy='dynamic',
            primaryjoin=sa.and_(
                ProposalSponsorMembership.subject_id == Account.id,
                ProposalSponsorMembership.is_invite,  # type: ignore[arg-type]
                ProposalSponsorMembership.revoked_at.is_(  # type: ignore[has-type]
                    None
                ),
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
