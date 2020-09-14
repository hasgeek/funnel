from sqlalchemy.ext.declarative import declared_attr

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .helpers import reopen
from .membership import ImmutableMembershipMixin
from .proposal import Proposal
from .user import User

__all__ = ['ProposalMembership']


class ProposalMembership(ImmutableMembershipMixin, db.Model):
    """
    Users can be presenters or reviewers on proposals.
    """

    __tablename__ = 'proposal_membership'

    # List of is_role columns in this model
    __data_columns__ = ('is_reviewer', 'is_presenter')

    __roles__ = {
        'all': {'read': {'urls', 'user', 'is_reviewer', 'is_presenter', 'proposal'}}
    }
    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_reviewer',
            'is_presenter',
            'user',
            'proposal',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'offered_roles',
            'is_reviewer',
            'is_presenter',
            'user',
        },
        'related': {'urls', 'uuid_b58', 'offered_roles', 'is_reviewer', 'is_presenter'},
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
                'memberships', lazy='dynamic', cascade='all', passive_deletes=True
            ),
        )
    )
    parent = immutable(db.synonym('proposal'))
    parent_id = immutable(db.synonym('proposal_id'))

    # Proposal roles (at least one must be True):

    #: Reviewers can change state of proposal
    is_reviewer = db.Column(db.Boolean, nullable=False, default=False)
    #: Presenters can edit and withdraw proposals
    is_presenter = db.Column(db.Boolean, nullable=False, default=False)

    @declared_attr
    def __table_args__(cls):
        args = list(super().__table_args__)
        args.append(
            db.CheckConstraint(
                db.or_(cls.is_reviewer.is_(True), cls.is_presenter.is_(True)),
                name='proposal_membership_has_role',
            )
        )
        return tuple(args)

    @cached_property
    def offered_roles(self):
        """Roles offered by this membership record"""
        roles = set()
        if self.is_reviewer:
            roles.add('reviewer')
        elif self.is_presenter:
            roles.add('presenter')
        return roles


# Project relationships: all crew, vs specific roles
@reopen(Proposal)
class Proposal:
    active_memberships = with_roles(
        db.relationship(
            ProposalMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                ProposalMembership.proposal_id == Proposal.id,
                ProposalMembership.is_active,
            ),
            viewonly=True,
        ),
        grants_via={'user': {'reviewer', 'presenter'}},
    )

    active_reviewer_memberships = db.relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            ProposalMembership.proposal_id == Proposal.id,
            ProposalMembership.is_active,
            ProposalMembership.is_reviewer.is_(True),
        ),
        viewonly=True,
    )

    active_presenter_memberships = db.relationship(
        ProposalMembership,
        lazy='dynamic',
        primaryjoin=db.and_(
            ProposalMembership.proposal_id == Proposal.id,
            ProposalMembership.is_active,
            ProposalMembership.is_presenter.is_(True),
        ),
        viewonly=True,
    )

    members = DynamicAssociationProxy('active_memberships', 'user')
    reviewers = DynamicAssociationProxy('active_reviewer_memberships', 'user')
    presenters = DynamicAssociationProxy('active_presenters_memberships', 'user')


@reopen(User)
class User:
    proposal_memberships = db.relationship(
        ProposalMembership,
        lazy='dynamic',
        foreign_keys=[ProposalMembership.user_id],
        viewonly=True,
    )
