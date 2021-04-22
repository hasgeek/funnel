from typing import Set

from sqlalchemy.ext.declarative import declared_attr

from werkzeug.utils import cached_property

from coaster.sqlalchemy import DynamicAssociationProxy, immutable, with_roles

from . import db
from .helpers import reopen
from .membership_mixin import MEMBERSHIP_RECORD_TYPE, ImmutableProfileMembershipMixin
from .profile import Profile
from .project import Project
from .reorder_mixin import ReorderMixin

__all__ = ['SponsorMembership']


class SponsorMembership(ReorderMixin, ImmutableProfileMembershipMixin, db.Model):
    """Sponsor of a project."""

    __tablename__ = 'sponsor_membership'

    # List of data columns in this model that must be copied into revisions
    __data_columns__ = ('seq', 'is_promoted', 'label')

    __roles__ = {
        'all': {'read': {'urls', 'profile', 'project', 'is_promoted', 'label', 'seq'}}
    }

    project_id = immutable(
        db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    )
    project = immutable(
        db.relationship(
            Project,
            backref=db.backref(
                'sponsor_memberships',
                lazy='dynamic',
                cascade='all',
                passive_deletes=True,
            ),
        )
    )
    parent = db.synonym('project')
    parent_id = db.synonym('project_id')

    #: Sequence number. Not immutable, and may be overwritten by ReorderMixin as a
    #: side-effect of reordering other records. This is not considered a revision.
    #: However, it can be argued that relocating a sponsor in the list constitutes a
    #: change that must be recorded as a revision. We may need to change our opinion
    #: on `seq` being mutable in a future iteration.
    seq = db.Column(db.Integer, nullable=False)

    #: Is this sponsor being promoted for commercial reasons? Projects may have a legal
    #: obligation to reveal this. This column records a declaration from the project.
    is_promoted = immutable(db.Column(db.Boolean, nullable=False))

    #: Optional label, indicating the type of sponsor
    label = immutable(db.Column(db.Unicode, nullable=True))

    # This model does not offer a large text field for promotional messages, since
    # revision control on such a field is a distinct problem from membership
    # revisioning. The planned Page model can be used instead, with this model getting
    # a page id reference column whenever that model is ready.

    @declared_attr
    def __table_args__(cls):
        """Table arguments."""
        args = list(super().__table_args__)
        # Add unique constraint on :attr:`seq` for active records
        args.append(
            db.Index(
                'ix_sponsor_membership_seq',
                'project_id',
                'seq',
                unique=True,
                postgresql_where=db.text('revoked_at IS NULL'),
            ),
        )
        return tuple(args)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Assign a default value to `seq`
        if self.seq is None:
            self.seq = db.select(
                [db.func.coalesce(db.func.max(SponsorMembership.seq) + 1, 1)]
            ).where(self.parent_scoped_reorder_query_filter)

    @property
    def parent_scoped_reorder_query_filter(self):
        """
        Return a query filter that includes a scope limitation to active records.

        Used by:
        * :meth:`__init__` to assign an initial sequence number, and
        * :class:`ReorderMixin` to reassign sequence numbers
        """
        cls = self.__class__
        # During __init__, if the constructor only received `project`, it doesn't yet
        # know `project_id`. Therefore we have to be prepared for two possible returns
        if self.project_id is not None:
            return db.and_(cls.project_id == self.project_id, cls.is_active)
        return db.and_(cls.project == self.project, cls.is_active)

    @cached_property
    def offered_roles(self) -> Set[str]:
        """Return empty set as this membership does not offer any roles on Project."""
        return set()


@reopen(Project)
class __Project:
    active_sponsor_memberships = with_roles(
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

    sponsors = DynamicAssociationProxy('active_sponsor_memberships', 'profile')


@reopen(Profile)
class __Profile:
    active_sponsor_memberships = with_roles(
        db.relationship(
            SponsorMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                SponsorMembership.profile_id == Profile.id,
                SponsorMembership.is_active,
            ),
            order_by=SponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'all'},
    )

    active_sponsor_membership_invites = with_roles(
        db.relationship(
            SponsorMembership,
            lazy='dynamic',
            primaryjoin=db.and_(
                SponsorMembership.profile_id == Profile.id,
                SponsorMembership.record_type == MEMBERSHIP_RECORD_TYPE.INVITE,  # type: ignore[has-type]
                SponsorMembership.is_active,
            ),
            order_by=SponsorMembership.granted_at.desc(),
            viewonly=True,
        ),
        read={'admin'},
    )
