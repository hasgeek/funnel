"""Proposal (submission) model, the primary content type within a project."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime as datetime_type
from typing import TYPE_CHECKING, Any, Self

from werkzeug.utils import cached_property

from baseframe import __
from baseframe.filters import preview
from coaster.sqlalchemy import (
    DynamicAssociationProxy,
    StateManager,
    role_check,
    with_roles,
)
from coaster.utils import LabeledEnum, NameTitle

from .account import Account
from .base import (
    BaseMixin,
    BaseScopedIdNameMixin,
    DynamicMapped,
    Mapped,
    Model,
    Query,
    TSVectorType,
    UuidMixin,
    db,
    relationship,
    sa,
    sa_orm,
)
from .helpers import (
    MarkdownCompositeDocument,
    add_search_trigger,
    visual_field_delimiter,
)
from .label import Label, ProposalLabelProxy, proposal_label
from .project import Project
from .project_membership import project_child_role_map
from .reorder_mixin import ReorderMixin
from .video_mixin import VideoMixin

__all__ = ['PROPOSAL_STATE', 'Proposal', 'ProposalSuuidRedirect']

_marker = object()


# MARK: Constants ----------------------------------------------------------------


class PROPOSAL_STATE(LabeledEnum):  # noqa: N801
    # Draft-state for future use, so people can save their proposals and submit only
    # when ready. If you add any new state, you need to add a migration to modify the
    # check constraint
    DRAFT = (1, NameTitle('draft', __("Draft")))
    SUBMITTED = (2, NameTitle('submitted', __("Submitted")))
    CONFIRMED = (3, NameTitle('confirmed', __("Confirmed")))
    WAITLISTED = (4, NameTitle('waitlisted', __("Waitlisted")))
    REJECTED = (6, NameTitle('rejected', __("Rejected")))
    CANCELLED = (7, NameTitle('cancelled', __("Cancelled")))
    AWAITING_DETAILS = (8, NameTitle('awaiting_details', __("Awaiting details")))
    UNDER_EVALUATION = (9, NameTitle('under_evaluation', __("Under evaluation")))
    DELETED = (12, NameTitle('deleted', __("Deleted")))
    TEMPLATE = (13, NameTitle('template', __("Template")))

    # These 3 are not in the editorial workflow anymore - Feb 23 2018
    SHORTLISTED = (5, NameTitle('shortlisted', __("Shortlisted")))
    SHORTLISTED_FOR_REHEARSAL = (
        10,
        NameTitle('shortlisted_for_rehearsal', __("Shortlisted for rehearsal")),
    )
    REHEARSAL = (11, NameTitle('rehearsal', __("Rehearsal ongoing")))

    # Groups
    PUBLIC = {  # States visible to the public
        SUBMITTED,
        CONFIRMED,
        WAITLISTED,
        REJECTED,
        CANCELLED,
        AWAITING_DETAILS,
        UNDER_EVALUATION,
    }
    CONFIRMABLE = {
        WAITLISTED,
        UNDER_EVALUATION,
        SHORTLISTED,
        SHORTLISTED_FOR_REHEARSAL,
        REHEARSAL,
    }
    REJECTABLE = {
        WAITLISTED,
        UNDER_EVALUATION,
        SHORTLISTED,
        SHORTLISTED_FOR_REHEARSAL,
        REHEARSAL,
    }
    WAITLISTABLE = {CONFIRMED, UNDER_EVALUATION}
    EVALUATEABLE = {SUBMITTED, AWAITING_DETAILS}
    DELETABLE = {
        DRAFT,
        SUBMITTED,
        CONFIRMED,
        WAITLISTED,
        REJECTED,
        AWAITING_DETAILS,
        UNDER_EVALUATION,
        TEMPLATE,
    }
    CANCELLABLE = {
        DRAFT,
        SUBMITTED,
        CONFIRMED,
        WAITLISTED,
        REJECTED,
        AWAITING_DETAILS,
        UNDER_EVALUATION,
    }
    UNDO_TO_SUBMITTED = {AWAITING_DETAILS, UNDER_EVALUATION, REJECTED}
    # SHORLISTABLE = {SUBMITTED, AWAITING_DETAILS, UNDER_EVALUATION}


# MARK: Models ----------------------------------------------------------------


class Proposal(UuidMixin, BaseScopedIdNameMixin, VideoMixin, ReorderMixin, Model):
    __tablename__ = 'proposal'

    created_by_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('account.id'), default=None, nullable=False
    )
    created_by: Mapped[Account] = with_roles(
        relationship(back_populates='created_proposals'),
        grants={'creator', 'participant'},
    )
    project_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('project.id'), default=None, nullable=False
    )
    project: Mapped[Project] = with_roles(
        relationship(back_populates='proposals'),
        grants_via={None: project_child_role_map},
    )
    parent_id: Mapped[int] = sa_orm.synonym('project_id')
    parent_id_column = 'project_id'
    parent: Mapped[Project] = sa_orm.synonym('project')

    #: Reuse the `url_id` column from BaseScopedIdNameMixin as a sorting order column.
    #: `url_id` was a public number on talkfunnel.com, but is private on hasgeek.com.
    #: Old values are now served as redirects from Nginx config, so the column is
    #: redundant and can be renamed pending a patch to the base class in Coaster. This
    #: number is no longer considered suitable for public display because it is assigned
    #: to all proposals, including drafts. A user-facing sequence will have gaps.
    #: Should numbering be required in the product, see `Update.number` for a better
    #: implementation.
    seq: Mapped[int] = sa_orm.synonym('url_id')  # type: ignore[assignment]

    # TODO: Stand-in for `submitted_at` until proposals have a workflow-driven datetime
    datetime: Mapped[datetime_type] = sa_orm.synonym('created_at')

    _state: Mapped[int] = sa_orm.mapped_column(
        'state',
        sa.SmallInteger,
        StateManager.check_constraint(
            'state', PROPOSAL_STATE, sa.SmallInteger, name='proposal_state_check'
        ),
        default=PROPOSAL_STATE.SUBMITTED,
        nullable=False,
    )
    state = StateManager['Proposal'](
        '_state', PROPOSAL_STATE, doc="Current state of the proposal"
    )

    commentset_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('commentset.id', ondelete='RESTRICT'), nullable=False
    )
    commentset: Mapped[Commentset] = relationship(
        uselist=False,
        lazy='joined',
        single_parent=True,
        cascade='save-update, merge, delete, delete-orphan',
        back_populates='proposal',
    )

    body, body_text, body_html = MarkdownCompositeDocument.create(
        'body', nullable=False, default=''
    )
    description: Mapped[str] = sa_orm.mapped_column(default='')
    custom_description: Mapped[bool] = sa_orm.mapped_column(default=False)
    template: Mapped[bool] = sa_orm.mapped_column(default=False)
    featured: Mapped[bool] = sa_orm.mapped_column(default=False)

    edited_at: Mapped[datetime_type | None] = sa_orm.mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )

    #: Revision number maintained by SQLAlchemy, starting at 1
    revisionid: Mapped[int] = with_roles(sa_orm.mapped_column(), read={'all'})

    search_vector: Mapped[str] = sa_orm.mapped_column(
        TSVectorType(
            'title',
            'description',
            'body_text',
            weights={
                'title': 'A',
                'description': 'B',
                'body_text': 'B',
            },
            regconfig='english',
            hltext=lambda: sa.func.concat_ws(
                visual_field_delimiter,
                Proposal.title,
                Proposal.body_html,
            ),
        ),
        nullable=False,
        deferred=True,
    )

    #: For reading and setting labels from the edit form
    formlabels = ProposalLabelProxy()

    labels: Mapped[list[Label]] = with_roles(
        relationship(Label, secondary=proposal_label, back_populates='proposals'),
        read={'all'},
    )

    all_memberships: DynamicMapped[ProposalMembership] = relationship(
        lazy='dynamic', passive_deletes=True, back_populates='proposal'
    )

    # This relationship does not use `lazy='dynamic'` because it is expected to contain
    # <2 records on average, and won't exceed 50 in the most extreme cases
    memberships: Mapped[list[ProposalMembership]] = with_roles(
        relationship(
            primaryjoin=lambda: sa.and_(
                ProposalMembership.proposal_id == Proposal.id,
                ProposalMembership.is_active,  # type: ignore[has-type]  # FIXME
            ),
            order_by=lambda: ProposalMembership.seq,
            viewonly=True,
        ),
        read={'all'},
        # These grants are authoritative and used instead of `offered_roles` above
        grants_via={'member': {'submitter', 'editor'}},
    )

    session: Mapped[Session | None] = relationship(
        uselist=False, back_populates='proposal'
    )

    all_sponsor_memberships: DynamicMapped[ProposalSponsorMembership] = relationship(
        lazy='dynamic', passive_deletes=True, back_populates='proposal'
    )
    sponsor_memberships: DynamicMapped[ProposalSponsorMembership] = with_roles(
        relationship(
            lazy='dynamic',
            primaryjoin=lambda: sa.and_(
                ProposalSponsorMembership.proposal_id == Proposal.id,
                ProposalSponsorMembership.is_active,  # type: ignore[has-type]  # FIXME
            ),
            order_by=lambda: ProposalSponsorMembership.seq,
            viewonly=True,
        ),
        read={'all'},
    )

    __table_args__ = (
        sa.UniqueConstraint(
            'project_id', 'url_id', name='proposal_project_id_url_id_key'
        ),
        sa.Index('ix_proposal_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __mapper_args__ = {'version_id_col': revisionid}

    __roles__ = {
        'all': {
            'read': {
                'absolute_url',  # From UrlForMixin
                'urls',
                'uuid_b58',
                'url_name_uuid_b58',
                'title',
                'body',
                'created_by',
                'first_user',
                'session',
                'project',
                'datetime',
            },
            'call': {'url_for', 'state', 'commentset', 'views', 'getprev', 'getnext'},
        },
        'project_editor': {
            'call': {
                'reorder_item',
                'reorder_before',
                'reorder_after',
            },
        },
    }

    __datasets__ = {
        'primary': {
            'absolute_url',
            'datetime',
            'urls',
            'uuid_b58',
            'url_name_uuid_b58',
            'title',
            'body',
            'created_by',
            'first_user',
            'session',
            'labels',
            'project',
        },
        'without_parent': {
            'absolute_url',
            'datetime',
            'urls',
            'uuid_b58',
            'url_name_uuid_b58',
            'title',
            'body',
            'created_by',
            'first_user',
            'labels',
            'session',
        },
        'related': {'absolute_url', 'uuid_b58', 'url_name_uuid_b58', 'title'},
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.commentset = Commentset(settype=SET_TYPE.PROPOSAL)
        # Assume self.created_by is set. Fail if not.
        db.session.add(
            ProposalMembership(
                proposal=self, member=self.created_by, granted_by=self.created_by
            )
        )

    def __repr__(self) -> str:
        """Represent :class:`Proposal` as a string."""
        return (
            f'<Proposal "{self.title}" in project "{self.project.title}"'
            f' by "{self.created_by.fullname}">'
        )

    def __str__(self) -> str:
        return self.title

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return self.title
        return format(self.title, format_spec)

    # State transitions
    state.add_conditional_state(
        'SCHEDULED',
        state.CONFIRMED,
        lambda proposal: proposal.session is not None and proposal.session.scheduled,
        lambda proposal: sa.and_(
            proposal.session.is_not(None), proposal.session.scheduled
        ),
        label=('scheduled', __("Confirmed &amp; scheduled")),
    )

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.AWAITING_DETAILS,
        state.DRAFT,
        title=__("Draft"),
        message=__("This proposal has been withdrawn"),
        type='danger',
    )
    def withdraw(self) -> None:
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.DRAFT,
        state.SUBMITTED,
        title=__("Submit"),
        message=__("This proposal has been submitted"),
        type='success',
    )
    def submit(self) -> None:
        pass

    # TODO: remove project_editor once ProposalMembership UI
    # has been implemented
    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.UNDO_TO_SUBMITTED,
        state.SUBMITTED,
        title=__("Send Back to Submitted"),
        message=__("This proposal has been submitted"),
        type='danger',
    )
    def undo_to_submitted(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.CONFIRMABLE,
        state.CONFIRMED,
        title=__("Confirm"),
        message=__("This proposal has been confirmed"),
        type='success',
    )
    def confirm(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.CONFIRMED,
        state.SUBMITTED,
        title=__("Unconfirm"),
        message=__("This proposal is no longer confirmed"),
        type='danger',
    )
    def unconfirm(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.WAITLISTABLE,
        state.WAITLISTED,
        title=__("Waitlist"),
        message=__("This proposal has been waitlisted"),
        type='primary',
    )
    def waitlist(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.REJECTABLE,
        state.REJECTED,
        title=__("Reject"),
        message=__("This proposal has been rejected"),
        type='danger',
    )
    def reject(self) -> None:
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.CANCELLABLE,
        state.CANCELLED,
        title=__("Cancel"),
        message=__("This proposal has been cancelled"),
        type='danger',
    )
    def cancel(self) -> None:
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.CANCELLED,
        state.SUBMITTED,
        title=__("Undo cancel"),
        message=__("This proposal’s cancellation has been reversed"),
        type='success',
    )
    def undo_cancel(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.SUBMITTED,
        state.AWAITING_DETAILS,
        title=__("Awaiting details"),
        message=__("Awaiting details for this proposal"),
        type='primary',
    )
    def awaiting_details(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.EVALUATEABLE,
        state.UNDER_EVALUATION,
        title=__("Under evaluation"),
        message=__("This proposal has been put under evaluation"),
        type='success',
    )
    def under_evaluation(self) -> None:
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.DELETABLE,
        state.DELETED,
        title=__("Delete"),
        message=__("This proposal has been deleted"),
        type='danger',
    )
    def delete(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.SUBMITTED,
        state.TEMPLATE,
        title=__("Convert to template"),
        message=__("This proposal has been converted into a template"),
        type='success',
    )
    def make_template(self) -> None:
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.TEMPLATE,
        state.SUBMITTED,
        title=__("Convert to submission"),
        message=__("This proposal has been converted into a submission"),
        type='success',
    )
    def undo_template(self) -> None:
        pass

    @property
    def first_user(self) -> Account:
        """Return the first credited member on the proposal, or creator if none."""
        for membership in self.memberships:
            if not membership.is_uncredited:
                return membership.member
        return self.created_by

    @with_roles(call={'project_editor'})
    def move_to(self, project: Project) -> None:
        """Move to a new project and reset :attr:`url_id`."""
        self.project = project
        # pylint: disable=attribute-defined-outside-init
        self.url_id = None
        self.make_scoped_id()

    def update_description(self) -> None:
        if not self.custom_description:
            self.description = preview(self.body_html)

    def getnext(self) -> Proposal | None:
        return (
            Proposal.query.filter(
                Proposal.project == self.project,
                Proposal.seq > self.seq,
            )
            .order_by(Proposal.seq.asc())
            .first()
        )

    def getprev(self) -> Proposal | None:
        return (
            Proposal.query.filter(
                Proposal.project == self.project,
                Proposal.seq < self.seq,
            )
            .order_by(Proposal.seq.desc())
            .first()
        )

    @with_roles(read={'all'})
    @cached_property
    def has_sponsors(self) -> bool:
        return db.session.query(self.sponsor_memberships.exists()).scalar()

    sponsors: DynamicAssociationProxy[Account, ProposalSponsorMembership] = (
        DynamicAssociationProxy('sponsor_memberships', 'member')
    )

    @role_check('reader')
    def has_reader_role(
        self, _actor: Account | None, _anchors: Sequence[Any] = ()
    ) -> bool:
        """Grant reader role if the proposal is not a draft."""
        return not self.state.DRAFT

    @role_check('commenter')
    def has_commenter_role(
        self, actor: Account | None, _anchors: Sequence[Any] = ()
    ) -> bool:
        """Grant 'commenter' role to any participant or submitter."""
        return self.roles_for(actor).has_any(('project_participant', 'submitter'))

    @classmethod
    def all_public(cls) -> Query[Self]:
        return cls.query.join(Project).filter(Project.state.PUBLISHED, cls.state.PUBLIC)

    @classmethod
    def get(  # type: ignore[override]  # pylint: disable=arguments-differ
        cls, uuid_b58: str
    ) -> Proposal | None:
        """Get a proposal by its public Base58 id."""
        return cls.query.filter_by(uuid_b58=uuid_b58).one_or_none()


add_search_trigger(Proposal, 'search_vector')


class ProposalSuuidRedirect(BaseMixin[int, Account], Model):
    """Holds Proposal SUUIDs from before when they were deprecated."""

    __tablename__ = 'proposal_suuid_redirect'

    suuid: Mapped[str] = sa_orm.mapped_column(
        sa.Unicode(22), nullable=False, index=True
    )
    proposal_id: Mapped[int] = sa_orm.mapped_column(
        sa.ForeignKey('proposal.id', ondelete='CASCADE'), default=None, nullable=False
    )
    proposal: Mapped[Proposal] = relationship()


# Tail imports
from .comment import SET_TYPE, Commentset
from .proposal_membership import ProposalMembership
from .sponsor_membership import ProposalSponsorMembership

if TYPE_CHECKING:
    from .session import Session
