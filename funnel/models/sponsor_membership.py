from __future__ import annotations

from typing import Set

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .helpers import reopen
from .membership_mixin import ImmutableProfileMembershipMixin, ReorderMembershipMixin
from .profile import Profile
from .project import Project
from .proposal import Proposal

__all__ = ['SponsorMembership', 'ProposalSponsorMembership']


class SponsorMembership(
    ReorderMembershipMixin, ImmutableProfileMembershipMixin, db.Model
):
    """Sponsor of a project."""

    __tablename__ = 'sponsor_membership'

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label')

    __roles__ = {
        'all': {'read': {'urls', 'profile', 'project', 'is_promoted', 'label', 'seq'}}
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_promoted',
            'label',
            'seq',
            'profile',
            'project',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_promoted',
            'label',
            'seq',
            'profile',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_promoted',
            'label',
            'seq',
        },
    }

    project_id = immutable(
        db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    )
    project = immutable(
        db.relationship(
            Project,
            backref=db.backref(
                'all_sponsor_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        )
    )
    parent = db.synonym('project')
    parent_id = db.synonym('project_id')

    #: Is this sponsor being promoted for commercial reasons? Projects may have a legal
    #: obligation to reveal this. This column records a declaration from the project.
    is_promoted = immutable(db.Column(db.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(
        db.Column(
            db.Unicode,
            db.CheckConstraint(
                db.column('label') != '', name='sponsor_membership_label_check'
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
        db.relationship(
            SponsorMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                SponsorMembership.project_id == Project.id,
                SponsorMembership.is_active,
            ),
            order_by=SponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self):
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy('sponsor_memberships', 'profile')


class ProposalSponsorMembership(
    ReorderMembershipMixin, ImmutableProfileMembershipMixin, db.Model
):
    """Sponsor of a proposal."""

    __tablename__ = 'proposal_sponsor_membership'

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label')

    __roles__ = {
        'all': {
            'read': {'urls', 'profile', 'proposal', 'is_promoted', 'label', 'seq'},
            'call': {'url_for'},
        }
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_promoted',
            'label',
            'seq',
            'profile',
            'proposal',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_promoted',
            'label',
            'seq',
            'profile',
        },
        'related': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_promoted',
            'label',
            'seq',
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
                'all_sponsor_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        )
    )
    parent = db.synonym('proposal')
    parent_id = db.synonym('proposal_id')

    #: Is this sponsor being promoted for commercial reasons? Proposals may have a legal
    #: obligation to reveal this. This column records a declaration from the proposal.
    is_promoted = immutable(db.Column(db.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(
        db.Column(
            db.Unicode,
            db.CheckConstraint(
                db.column('label') != '', name='proposal_sponsor_membership_label_check'
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
        db.relationship(
            ProposalSponsorMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
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
    def has_sponsors(self):
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors = DynamicAssociationProxy('sponsor_memberships', 'profile')


@reopen(Profile)
class __Profile:
    sponsor_memberships = db.relationship(
        SponsorMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            SponsorMembership.profile_id == Profile.id,
            SponsorMembership.is_active,
        ),
        order_by=SponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    sponsor_membership_invites = with_roles(
        db.relationship(
            SponsorMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                SponsorMembership.profile_id == Profile.id,
                SponsorMembership.is_invite,
                SponsorMembership.is_active,
            ),
            order_by=SponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'admin'},
    )

    proposal_sponsor_memberships = db.relationship(
        ProposalSponsorMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            ProposalSponsorMembership.profile_id == Profile.id,
            ProposalSponsorMembership.is_active,
        ),
        order_by=ProposalSponsorMembership.granted_at.desc(),
        viewonly=True,
    )

    proposal_sponsor_membership_invites = with_roles(
        db.relationship(
            ProposalSponsorMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                ProposalSponsorMembership.profile_id == Profile.id,
                ProposalSponsorMembership.is_invite,
                ProposalSponsorMembership.is_active,
            ),
            order_by=ProposalSponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'admin'},
    )
