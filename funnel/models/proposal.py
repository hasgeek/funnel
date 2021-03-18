from __future__ import annotations

from typing import Iterable, Optional, Set

from sqlalchemy.ext.hybrid import hybrid_property

from werkzeug.utils import cached_property

from baseframe import __
from coaster.sqlalchemy import SqlSplitIdComparator, StateManager, with_roles
from coaster.utils import LabeledEnum

from ..utils import geonameid_from_location
from . import (
    BaseMixin,
    BaseScopedIdNameMixin,
    MarkdownColumn,
    TimestampMixin,
    TSVectorType,
    UrlType,
    UuidMixin,
    db,
)
from .commentvote import SET_TYPE, Commentset, Voteset
from .email_address import EmailAddressMixin
from .helpers import add_search_trigger, reopen, visual_field_delimiter
from .project import Project
from .project_membership import project_child_role_map
from .user import User
from .video import VideoMixin

__all__ = ['PROPOSAL_STATE', 'Proposal', 'ProposalRedirect', 'ProposalSuuidRedirect']

_marker = object()


# --- Constants ------------------------------------------------------------------


class PROPOSAL_STATE(LabeledEnum):  # NOQA: N801
    # Draft-state for future use, so people can save their proposals and submit only when ready
    # If you add any new state, you need to add a migration to modify the check constraint
    DRAFT = (0, 'draft', __("Draft"))
    SUBMITTED = (1, 'submitted', __("Submitted"))
    CONFIRMED = (2, 'confirmed', __("Confirmed"))
    WAITLISTED = (3, 'waitlisted', __("Waitlisted"))
    REJECTED = (5, 'rejected', __("Rejected"))
    CANCELLED = (6, 'cancelled', __("Cancelled"))
    AWAITING_DETAILS = (7, 'awaiting_details', __("Awaiting details"))
    UNDER_EVALUATION = (8, 'under_evaluation', __("Under evaluation"))
    DELETED = (11, 'deleted', __("Deleted"))

    # These 3 are not in the editorial workflow anymore - Feb 23 2018
    SHORTLISTED = (4, 'shortlisted', __("Shortlisted"))
    SHORTLISTED_FOR_REHEARSAL = (
        9,
        'shortlisted_for_rehearsal',
        __("Shortlisted for rehearsal"),
    )
    REHEARSAL = (10, 'rehearsal', __("Rehearsal ongoing"))

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


class Proposal(
    UuidMixin,
    EmailAddressMixin,  # TODO: Remove this, email is in user account anyway
    BaseScopedIdNameMixin,
    VideoMixin,
    db.Model,
):
    __tablename__ = 'proposal'
    __email_for__ = 'owner'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = with_roles(
        db.relationship(
            User,
            primaryjoin=user_id == User.id,
            backref=db.backref('proposals', cascade='all', lazy='dynamic'),
        ),
        grants={'creator'},
    )

    speaker_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    speaker = with_roles(
        db.relationship(
            User,
            primaryjoin=speaker_id == User.id,
            lazy='joined',
            backref=db.backref('speaker_at', cascade='all', lazy='dynamic'),
        ),
        grants={'presenter'},
    )

    # TODO: Remove this, phone is in user account anyway
    phone = db.Column(db.Unicode(80), nullable=True)

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(
            Project,
            primaryjoin=project_id == Project.id,
            backref=db.backref(
                'proposals', cascade='all', lazy='dynamic', order_by='Proposal.url_id'
            ),
        ),
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')

    # TODO: Deprecated
    abstract = MarkdownColumn('abstract', nullable=True)
    # TODO: Deprecated
    outline = MarkdownColumn('outline', nullable=True)
    # TODO: Deprecated
    requirements = MarkdownColumn('requirements', nullable=True)
    # TODO: Deprecated
    slides = db.Column(UrlType, nullable=True)
    # TODO: Deprecated
    links = db.Column(db.Text, default='', nullable=True)
    # TODO: Deprecated
    bio = MarkdownColumn('bio', nullable=True)

    _state = db.Column(
        'state',
        db.Integer,
        StateManager.check_constraint('state', PROPOSAL_STATE),
        default=PROPOSAL_STATE.SUBMITTED,
        nullable=False,
    )
    state = StateManager('_state', PROPOSAL_STATE, doc="Current state of the proposal")

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(
        Voteset, uselist=False, lazy='joined', cascade='all', single_parent=True
    )

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(
        Commentset,
        uselist=False,
        lazy='joined',
        cascade='all',
        single_parent=True,
        back_populates='proposal',
    )

    body = MarkdownColumn('body', nullable=False, default='')
    description = db.Column(db.Unicode, nullable=False, default='')
    custom_description = db.Column(db.Boolean, nullable=False, default=False)
    template = db.Column(db.Boolean, nullable=False, default=False)
    featured = db.Column(db.Boolean, nullable=False, default=False)

    edited_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    # TODO: Deprecated, take from proposer profile
    location = db.Column(db.Unicode(80), nullable=False, default='')

    search_vector = db.deferred(
        db.Column(
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
                hltext=lambda: db.func.concat_ws(
                    visual_field_delimiter,
                    Proposal.title,
                    User.fullname,
                    Proposal.body_html,
                ),
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        db.UniqueConstraint('project_id', 'url_id'),
        db.Index('ix_proposal_search_vector', 'search_vector', postgresql_using='gin'),
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
                'speaker',
                'owner',
                'speaking',
                'bio',  # TODO: Deprecated
                'abstract',  # TODO: Deprecated
                'outline',  # TODO: Deprecated
                'requirements',  # TODO: Deprecated
                'slides',  # TODO: Deprecated
                'video',
                'links',  # TODO: Deprecated
                'location',  # TODO: Deprecated
                'session',
                'project',
                'datetime',
            },
            'call': {'url_for', 'state', 'commentset'},
        },
        'reviewer': {'read': {'email', 'phone'}},
        'project_editor': {'read': {'email', 'phone'}},
    }

    __datasets__ = {
        'primary': {
            'urls',
            'uuid_b58',
            'url_name_uuid_b58',
            'title',
            'body',
            'user',
            'speaker',
            'speaking',
            'bio',  # TODO: Deprecated
            'abstract',  # TODO: Deprecated
            'outline',  # TODO: Deprecated
            'requirements',  # TODO: Deprecated
            'slides',  # TODO: Deprecated
            'video',
            'links',  # TODO: Deprecated
            'location',  # TODO: Deprecated
            'session',
            'project',
            'email',  # TODO: Deprecated
            'phone',  # TODO: Deprecated
        },
        'without_parent': {
            'urls',
            'uuid_b58',
            'url_name_uuid_b58',
            'title',
            'body',
            'user',
            'speaker',
            'speaking',
            'bio',  # TODO: Deprecated
            'abstract',  # TODO: Deprecated
            'outline',  # TODO: Deprecated
            'requirements',  # TODO: Deprecated
            'slides',  # TODO: Deprecated
            'video',
            'links',  # TODO: Deprecated
            'location',  # TODO: Deprecated
            'session',
            'email',  # TODO: Deprecated
            'phone',  # TODO: Deprecated
        },
        'related': {'urls', 'uuid_b58', 'url_name_uuid_b58', 'title'},
    }

    def __init__(self, **kwargs) -> None:
        super(Proposal, self).__init__(**kwargs)
        self.voteset = Voteset(settype=SET_TYPE.PROPOSAL)
        self.commentset = Commentset(settype=SET_TYPE.PROPOSAL)

    def __repr__(self):
        """Represent :class:`Proposal` as a string."""
        return '<Proposal "{proposal}" in project "{project}" by "{user}">'.format(
            proposal=self.title, project=self.project.title, user=self.owner.fullname
        )

    @db.validates('project')
    def _validate_project(self, key, value):
        if not value:
            raise ValueError(value)

        if value != self.project and self.project is not None:
            redirect = ProposalRedirect.query.get((self.project_id, self.url_id))
            if redirect is None:
                redirect = ProposalRedirect(
                    project=self.project, url_id=self.url_id, proposal=self
                )
                db.session.add(redirect)
            else:
                redirect.proposal = self
        return value

    # State transitions
    state.add_conditional_state(
        'SCHEDULED',
        state.CONFIRMED,
        lambda proposal: proposal.session is not None and proposal.session.scheduled,
        label=('scheduled', __("Confirmed &amp; scheduled")),
    )

    @with_roles(call={'creator'})
    @state.transition(
        state.AWAITING_DETAILS,
        state.DRAFT,
        title=__("Draft"),
        message=__("This proposal has been withdrawn"),
        type='danger',
    )
    def withdraw(self):
        pass

    @with_roles(call={'creator'})
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
    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.UNDO_TO_SUBMITTED,
        state.SUBMITTED,
        title=__("Send Back to Submitted"),
        message=__("This proposal has been submitted"),
        type='danger',
    )
    def undo_to_submitted(self):
        pass

    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.CONFIRMABLE,
        state.CONFIRMED,
        title=__("Confirm"),
        message=__("This proposal has been confirmed"),
        type='success',
    )
    def confirm(self):
        pass

    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.CONFIRMED,
        state.SUBMITTED,
        title=__("Unconfirm"),
        message=__("This proposal is no longer confirmed"),
        type='danger',
    )
    def unconfirm(self):
        pass

    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.WAITLISTABLE,
        state.WAITLISTED,
        title=__("Waitlist"),
        message=__("This proposal has been waitlisted"),
        type='primary',
    )
    def waitlist(self):
        pass

    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.REJECTABLE,
        state.REJECTED,
        title=__("Reject"),
        message=__("This proposal has been rejected"),
        type='danger',
    )
    def reject(self):
        pass

    @with_roles(call={'creator'})
    @state.transition(
        state.CANCELLABLE,
        state.CANCELLED,
        title=__("Cancel"),
        message=__("This proposal has been cancelled"),
        type='danger',
    )
    def cancel(self):
        pass

    @with_roles(call={'creator'})
    @state.transition(
        state.CANCELLED,
        state.SUBMITTED,
        title=__("Undo cancel"),
        message=__("This proposal's cancellation has been reversed"),
        type='success',
    )
    def undo_cancel(self):
        pass

    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.SUBMITTED,
        state.AWAITING_DETAILS,
        title=__("Awaiting details"),
        message=__("Awaiting details for this proposal"),
        type='primary',
    )
    def awaiting_details(self):
        pass

    @with_roles(call={'project_editor', 'reviewer'})
    @state.transition(
        state.EVALUATEABLE,
        state.UNDER_EVALUATION,
        title=__("Under evaluation"),
        message=__("This proposal has been put under evaluation"),
        type='success',
    )
    def under_evaluation(self):
        pass

    @with_roles(call={'creator'})
    @state.transition(
        state.DELETABLE,
        state.DELETED,
        title=__("Delete"),
        message=__("This proposal has been deleted"),
        type='danger',
    )
    def delete(self):
        pass

    # These 3 transitions are not in the editorial workflow anymore - Feb 23 2018

    # @with_roles(call={'project_editor'})
    # @state.transition(state.SUBMITTED, state.SHORTLISTED, title=__("Shortlist"), message=__("This proposal has been shortlisted"), type='success')
    # def shortlist(self):
    #     pass

    # @with_roles(call={'project_editor'})
    # @state.transition(state.SHORLISTABLE, state.SHORTLISTED_FOR_REHEARSAL, title=__("Shortlist for rehearsal"), message=__("This proposal has been shortlisted for rehearsal"), type='success')
    # def shortlist_for_rehearsal(self):
    #     pass

    # @with_roles(call={'project_editor'})
    # @state.transition(state.SHORTLISTED_FOR_REHEARSAL, state.REHEARSAL, title=__("Rehearsal ongoing"), message=__("Rehearsal is now ongoing for this proposal"), type='success')
    # def rehearsal_ongoing(self):
    #     pass

    @with_roles(call={'project_editor', 'reviewer'})
    def move_to(self, project):
        """Move to a new project and reset :attr:`url_id`."""
        self.project = project
        self.url_id = None
        self.make_id()

    @with_roles(call={'project_editor', 'reviewer'})
    def transfer_to(self, user):
        """Transfer the proposal to a new user and speaker."""
        self.speaker = user

    @property
    def owner(self):
        return self.speaker or self.user

    @property
    def speaking(self):
        return self.speaker == self.user

    @speaking.setter
    def speaking(self, value):
        if value:
            self.speaker = self.user
        else:
            if self.speaker == self.user:
                self.speaker = None  # Reset only if it's currently set to user

    @hybrid_property
    def datetime(self):
        return self.created_at  # Until proposals have a workflow-driven datetime

    @cached_property
    def has_outstation_speaker(self) -> bool:
        """Verify if geocoded proposal location field differs from project location."""
        if not self.location:
            return False
        geonameid = geonameid_from_location(self.location)
        return bool(geonameid) and self.project.location_geonameid.isdisjoint(geonameid)

    def update_description(self) -> None:
        if not self.custom_description:
            body = self.body_text.strip()
            if body:
                self.description = body.splitlines()[0]
            else:
                self.description = ''

    def getnext(self):
        return (
            Proposal.query.filter(Proposal.project == self.project)
            .filter(Proposal.id != self.id)
            .filter(Proposal._state == self.state.value)
            .filter(Proposal.created_at < self.created_at)
            .order_by(db.desc('created_at'))
            .first()
        )

    def getprev(self):
        return (
            Proposal.query.filter(Proposal.project == self.project)
            .filter(Proposal.id != self.id)
            .filter(Proposal._state == self.state.value)
            .filter(Proposal.created_at > self.created_at)
            .order_by('created_at')
            .first()
        )

    def votes_count(self):
        return len(self.voteset.votes)

    def permissions(self, user: Optional[User], inherited: Optional[Set] = None) -> Set:
        perms = super(Proposal, self).permissions(user, inherited)
        if user is not None:
            perms.update(('vote_proposal', 'new_comment', 'vote_comment'))
            if user == self.owner:
                perms.update(
                    (
                        'view-proposal',
                        'edit_proposal',
                        'delete-proposal',  # FIXME: Prevent deletion of confirmed proposals
                        'submit-proposal',  # For workflows, to confirm the form is ready for submission (from draft state)
                        'transfer-proposal',
                    )
                )
                if self.speaker != self.user:
                    perms.add('decline-proposal')  # Decline speaking
        return perms

    def roles_for(self, actor: Optional[User], anchors: Iterable = ()) -> Set:
        roles = super(Proposal, self).roles_for(actor, anchors)
        if self.state.DRAFT:
            if 'reader' in roles:
                # https://github.com/hasgeek/funnel/pull/220#discussion_r168724439
                roles.remove('reader')
        else:
            roles.add('reader')

        # remove the owner check after proposal membership is implemented
        if self.owner == actor or roles.has_any(
            ('project_participant', 'presenter', 'reviewer')
        ):
            roles.add('commenter')

        return roles

    @classmethod
    def all_public(cls):
        return cls.query.join(Project).filter(Project.state.PUBLISHED, cls.state.PUBLIC)

    def reorder(self, below_proposal: Optional[Proposal] = None) -> int:
        ordered_siblings: list = self.project.proposals.order_by(
            Proposal.url_id.asc()
        ).all()
        ordered_siblings.remove(self)

        if below_proposal is None:
            # current item was moved to the top of the list
            ordered_siblings.insert(0, self)
        elif below_proposal == ordered_siblings[-1]:
            # current item has been pulled to the end of the list
            ordered_siblings.insert(len(ordered_siblings), self)
        else:
            ordered_siblings.insert(ordered_siblings.index(below_proposal) + 1, self)

        db.session.bulk_update_mappings(
            self.__class__,
            [
                {'id': p.id, 'project_id': p.project_id, 'url_id': (idx + 1) * 10000}
                for idx, p in enumerate(ordered_siblings)
            ],
        )
        db.session.bulk_update_mappings(
            self.__class__,
            [
                {'id': p.id, 'project_id': p.project_id, 'url_id': (idx + 1)}
                for idx, p in enumerate(ordered_siblings)
            ],
        )
        return ordered_siblings.index(self) + 1


add_search_trigger(Proposal, 'search_vector')


class ProposalRedirect(TimestampMixin, db.Model):
    __tablename__ = 'proposal_redirect'

    project_id = db.Column(
        None, db.ForeignKey('project.id'), nullable=False, primary_key=True
    )
    project = db.relationship(
        Project,
        primaryjoin=project_id == Project.id,
        backref=db.backref('proposal_redirects', cascade='all'),
    )
    parent = db.synonym('project')
    url_id = db.Column(db.Integer, nullable=False, primary_key=True)

    proposal_id = db.Column(
        None, db.ForeignKey('proposal.id', ondelete='SET NULL'), nullable=True
    )
    proposal = db.relationship(Proposal, backref='redirects')

    @hybrid_property
    def url_id_name(self):
        """
        Return :attr:`url_id` as a string.

        This property is also available as :attr:`url_name` for legacy reasons. This
        property will likely never be called directly on an instance. It exists for the
        SQL comparator that will be called to load the instance.
        """
        return str(self.url_id)

    @url_id_name.comparator  # type: ignore[no-redef]
    def url_id_name(cls):  # NOQA: N805
        return SqlSplitIdComparator(cls.url_id, splitindex=0)

    url_name = url_id_name  # Legacy name

    def __repr__(self):
        """Represent :class:`ProposalRedirect` as a string."""
        return '<ProposalRedirect %s/%s/%s: %s/%s/%s>' % (
            self.project.profile.name,
            self.project.name,
            self.url_id,
            self.proposal.project.profile.name if self.proposal else "(none)",
            self.proposal.project.name if self.proposal else "(none)",
            self.proposal.url_id if self.proposal else "(none)",
        )

    def redirect_view_args(self):
        if self.proposal:
            return {
                'profile': self.proposal.project.profile.name,
                'project': self.proposal.project.name,
                'proposal': self.proposal.url_name,
            }
        else:
            return {}


class ProposalSuuidRedirect(BaseMixin, db.Model):
    """Holds Proposal SUUIDs from before when they were deprecated."""

    __tablename__ = 'proposal_suuid_redirect'

    suuid = db.Column(db.Unicode(22), nullable=False, index=True)
    proposal_id = db.Column(
        None, db.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False
    )
    proposal = db.relationship(Proposal)


@reopen(Commentset)
class Commentset:  # type: ignore[no-redef]  # skipcq: PYL-E0102
    proposal = with_roles(
        db.relationship(Proposal, uselist=False, back_populates='commentset'),
        # TODO: Remove creator to subscriber mapping when proposals use memberships
        grants_via={
            None: {'presenter': 'document_subscriber', 'creator': 'document_subscriber'}
        },
    )


@reopen(Project)
class Project:  # type: ignore[no-redef]  # skipcq: PYL-E0102
    @property
    def proposals_all(self):
        if self.subprojects:
            return Proposal.query.filter(
                Proposal.project_id.in_([self.id] + [s.id for s in self.subprojects])
            )
        else:
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
            ).order_by(db.desc('created_at'))
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
            .order_by(db.desc('created_at'))
            .all(),
            'unconfirmed': basequery.filter(
                ~(Proposal.state.CONFIRMED),
                ~(Proposal.state.DRAFT),
                ~(Proposal.state.DELETED),
            )
            .order_by(db.desc('created_at'))
            .all(),
        }
