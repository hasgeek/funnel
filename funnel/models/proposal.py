"""Proposal (submission) model, the primary content type within a project."""

from __future__ import annotations

from typing import Iterable, Optional

from baseframe import __
from coaster.sqlalchemy import LazyRoleSet, StateManager, with_roles
from coaster.utils import LabeledEnum

from . import (
    BaseMixin,
    BaseScopedIdNameMixin,
    Mapped,
    TSVectorType,
    UuidMixin,
    db,
    markdown_cached_column,
    sa,
)
from .comment import SET_TYPE, Commentset
from .helpers import add_search_trigger, reopen, visual_field_delimiter
from .project import Project
from .project_membership import project_child_role_map
from .reorder_mixin import ReorderMixin
from .user import User
from .video_mixin import VideoMixin

__all__ = ['PROPOSAL_STATE', 'Proposal', 'ProposalSuuidRedirect']

_marker = object()


# --- Constants ------------------------------------------------------------------


class PROPOSAL_STATE(LabeledEnum):  # noqa: N801
    # Draft-state for future use, so people can save their proposals and submit only
    # when ready. If you add any new state, you need to add a migration to modify the
    # check constraint
    DRAFT = (1, 'draft', __("Draft"))
    SUBMITTED = (2, 'submitted', __("Submitted"))
    CONFIRMED = (3, 'confirmed', __("Confirmed"))
    WAITLISTED = (4, 'waitlisted', __("Waitlisted"))
    REJECTED = (6, 'rejected', __("Rejected"))
    CANCELLED = (7, 'cancelled', __("Cancelled"))
    AWAITING_DETAILS = (8, 'awaiting_details', __("Awaiting details"))
    UNDER_EVALUATION = (9, 'under_evaluation', __("Under evaluation"))
    DELETED = (12, 'deleted', __("Deleted"))

    # These 3 are not in the editorial workflow anymore - Feb 23 2018
    SHORTLISTED = (5, 'shortlisted', __("Shortlisted"))
    SHORTLISTED_FOR_REHEARSAL = (
        10,
        'shortlisted_for_rehearsal',
        __("Shortlisted for rehearsal"),
    )
    REHEARSAL = (11, 'rehearsal', __("Rehearsal ongoing"))

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


# --- Models ------------------------------------------------------------------


class Proposal(  # type: ignore[misc]
    UuidMixin,
    BaseScopedIdNameMixin,
    VideoMixin,
    ReorderMixin,
    db.Model,  # type: ignore[name-defined]
):
    __tablename__ = 'proposal'

    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    user = with_roles(
        sa.orm.relationship(
            User,
            primaryjoin=user_id == User.id,
            backref=sa.orm.backref('created_proposals', cascade='all', lazy='dynamic'),
        ),
        grants={'creator', 'participant'},
    )
    project_id = sa.Column(sa.Integer, sa.ForeignKey('project.id'), nullable=False)
    project: sa.orm.relationship[Project] = with_roles(
        sa.orm.relationship(
            Project,
            primaryjoin=project_id == Project.id,
            backref=sa.orm.backref(
                'proposals', cascade='all', lazy='dynamic', order_by='Proposal.url_id'
            ),
        ),
        grants_via={None: project_child_role_map},
    )
    parent_id = sa.orm.synonym('project_id')
    parent = sa.orm.synonym('project')

    #: Reuse the `url_id` column from BaseScopedIdNameMixin as a sorting order column.
    #: `url_id` was a public number on talkfunnel.com, but is private on hasgeek.com.
    #: Old values are now served as redirects from Nginx config, so the column is
    #: redundant and can be renamed pending a patch to the base class in Coaster. This
    #: number is no longer considered suitable for public display because it is assigned
    #: to all proposals, including drafts. A user-facing sequence will have gaps.
    #: Should numbering be required in the product, see `Update.number` for a better
    #: implementation.
    seq: Mapped[int] = sa.orm.synonym('url_id')

    # TODO: Stand-in for `submitted_at` until proposals have a workflow-driven datetime
    datetime = sa.orm.synonym('created_at')

    _state = sa.Column(
        'state',
        sa.Integer,
        StateManager.check_constraint('state', PROPOSAL_STATE),
        default=PROPOSAL_STATE.SUBMITTED,
        nullable=False,
    )
    state = StateManager('_state', PROPOSAL_STATE, doc="Current state of the proposal")

    commentset_id = sa.Column(
        sa.Integer, sa.ForeignKey('commentset.id'), nullable=False
    )
    commentset = sa.orm.relationship(
        Commentset,
        uselist=False,
        lazy='joined',
        cascade='all',
        single_parent=True,
        back_populates='proposal',
    )

    body = markdown_cached_column(
        'body', profile='document', nullable=False, default=''
    )
    description = sa.Column(sa.Unicode, nullable=False, default='')
    custom_description = sa.Column(sa.Boolean, nullable=False, default=False)
    template = sa.Column(sa.Boolean, nullable=False, default=False)
    featured = sa.Column(sa.Boolean, nullable=False, default=False)

    edited_at = sa.Column(sa.TIMESTAMP(timezone=True), nullable=True)

    search_vector = sa.orm.deferred(
        sa.Column(
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
        )
    )

    __table_args__ = (
        sa.UniqueConstraint(
            'project_id', 'url_id', name='proposal_project_id_url_id_key'
        ),
        sa.Index('ix_proposal_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __roles__ = {
        'all': {
            'read': {
                'urls',
                'uuid_b58',
                'url_name_uuid_b58',
                'title',
                'body',
                'user',
                'first_user',
                'session',
                'project',
                'datetime',
            },
            'call': {'url_for', 'state', 'commentset', 'views', 'getprev', 'getnext'},
        },
        'project_editor': {
            'call': {'reorder_item', 'reorder_before', 'reorder_after'},
        },
    }

    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'url_name_uuid_b58',
            'title',
            'body',
            'user',
            'first_user',
            'session',
            'project',
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'url_name_uuid_b58',
            'title',
            'body',
            'user',
            'first_user',
            'session',
        },
        'related': {'urls', 'uuid_b58', 'url_name_uuid_b58', 'title'},
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.commentset = Commentset(settype=SET_TYPE.PROPOSAL)
        # Assume self.user is set. Fail if not.
        db.session.add(
            ProposalMembership(proposal=self, user=self.user, granted_by=self.user)
        )

    def __repr__(self) -> str:
        """Represent :class:`Proposal` as a string."""
        return (
            f'<Proposal "{self.title}" in project "{self.project.title}"'
            f' by "{self.user.fullname}">'
        )

    # State transitions
    state.add_conditional_state(
        'SCHEDULED',
        state.CONFIRMED,
        lambda proposal: proposal.session is not None and proposal.session.scheduled,
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
    def withdraw(self):
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.DRAFT,
        state.SUBMITTED,
        title=__("Submit"),
        message=__("This proposal has been submitted"),
        type='success',
    )
    def submit(self):
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
    def undo_to_submitted(self):
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.CONFIRMABLE,
        state.CONFIRMED,
        title=__("Confirm"),
        message=__("This proposal has been confirmed"),
        type='success',
    )
    def confirm(self):
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.CONFIRMED,
        state.SUBMITTED,
        title=__("Unconfirm"),
        message=__("This proposal is no longer confirmed"),
        type='danger',
    )
    def unconfirm(self):
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.WAITLISTABLE,
        state.WAITLISTED,
        title=__("Waitlist"),
        message=__("This proposal has been waitlisted"),
        type='primary',
    )
    def waitlist(self):
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.REJECTABLE,
        state.REJECTED,
        title=__("Reject"),
        message=__("This proposal has been rejected"),
        type='danger',
    )
    def reject(self):
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.CANCELLABLE,
        state.CANCELLED,
        title=__("Cancel"),
        message=__("This proposal has been cancelled"),
        type='danger',
    )
    def cancel(self):
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.CANCELLED,
        state.SUBMITTED,
        title=__("Undo cancel"),
        message=__("This proposal's cancellation has been reversed"),
        type='success',
    )
    def undo_cancel(self):
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.SUBMITTED,
        state.AWAITING_DETAILS,
        title=__("Awaiting details"),
        message=__("Awaiting details for this proposal"),
        type='primary',
    )
    def awaiting_details(self):
        pass

    @with_roles(call={'project_editor'})  # skipcq: PTC-W0049
    @state.transition(
        state.EVALUATEABLE,
        state.UNDER_EVALUATION,
        title=__("Under evaluation"),
        message=__("This proposal has been put under evaluation"),
        type='success',
    )
    def under_evaluation(self):
        pass

    @with_roles(call={'creator'})  # skipcq: PTC-W0049
    @state.transition(
        state.DELETABLE,
        state.DELETED,
        title=__("Delete"),
        message=__("This proposal has been deleted"),
        type='danger',
    )
    def delete(self):
        pass

    @with_roles(call={'project_editor'})
    def move_to(self, project):
        """Move to a new project and reset :attr:`url_id`."""
        self.project = project
        self.url_id = None  # pylint: disable=attribute-defined-outside-init
        self.make_id()

    def update_description(self) -> None:
        if not self.custom_description:
            body = self.body_text.strip()
            if body:
                self.description = body.splitlines()[0]
            else:
                self.description = ''

    def getnext(self):
        return (
            Proposal.query.filter(
                Proposal.project == self.project,
                Proposal.seq > self.seq,
            )
            .order_by(Proposal.seq.asc())
            .first()
        )

    def getprev(self):
        return (
            Proposal.query.filter(
                Proposal.project == self.project,
                Proposal.seq < self.seq,
            )
            .order_by(Proposal.seq.desc())
            .first()
        )

    def roles_for(
        self, actor: Optional[User] = None, anchors: Iterable = ()
    ) -> LazyRoleSet:
        roles = super().roles_for(actor, anchors)
        if self.state.DRAFT:
            if 'reader' in roles:
                # https://github.com/hasgeek/funnel/pull/220#discussion_r168724439
                roles.remove('reader')
        else:
            roles.add('reader')

        if roles.has_any(('project_participant', 'submitter')):
            roles.add('commenter')

        return roles

    @classmethod
    def all_public(cls):
        return cls.query.join(Project).filter(Project.state.PUBLISHED, cls.state.PUBLIC)

    @classmethod
    def get(cls, uuid_b58):  # pylint: disable=arguments-differ
        """Get a proposal by its public Base58 id."""
        return cls.query.filter_by(uuid_b58=uuid_b58).one_or_none()


add_search_trigger(Proposal, 'search_vector')


class ProposalSuuidRedirect(BaseMixin, db.Model):  # type: ignore[name-defined]
    """Holds Proposal SUUIDs from before when they were deprecated."""

    __tablename__ = 'proposal_suuid_redirect'

    suuid = sa.Column(sa.Unicode(22), nullable=False, index=True)
    proposal_id = sa.Column(
        sa.Integer, sa.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
    )
    proposal = sa.orm.relationship(Proposal)


@reopen(Commentset)
class __Commentset:
    proposal = sa.orm.relationship(Proposal, uselist=False, back_populates='commentset')


@reopen(Project)
class __Project:
    @property
    def proposals_all(self):
        if self.subprojects:
            return Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        return self.proposals

    @property
    def proposals_by_state(self):
        if self.subprojects:
            basequery = Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            basequery = Proposal.query.filter_by(project=self)
        return Proposal.state.group(
            basequery.filter(
                ~(Proposal.state.DRAFT), ~(Proposal.state.DELETED)
            ).order_by(sa.desc('created_at'))
        )

    @property
    def proposals_by_confirmation(self):
        if self.subprojects:
            basequery = Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
            basequery = Proposal.query.filter_by(project=self)
        return {
            'confirmed': basequery.filter(Proposal.state.CONFIRMED)
            .order_by(sa.desc('created_at'))
            .all(),
            'unconfirmed': basequery.filter(
                ~(Proposal.state.CONFIRMED),
                ~(Proposal.state.DRAFT),
                ~(Proposal.state.DELETED),
            )
            .order_by(sa.desc('created_at'))
            .all(),
        }

    # Whether the project has any featured proposals. Returns `None` instead of
    # a boolean if the project does not have any proposal.
    _has_featured_proposals = sa.orm.column_property(
        sa.exists()
        .where(Proposal.project_id == Project.id)
        .where(Proposal.featured.is_(True))
        .correlate_except(Proposal),  # type: ignore[arg-type]
        deferred=True,
    )

    @property
    def has_featured_proposals(self) -> bool:
        return bool(self._has_featured_proposals)

    with_roles(has_featured_proposals, read={'all'})


# Tail imports
# pylint: disable=wrong-import-position
from .proposal_membership import ProposalMembership  # isort:skip
