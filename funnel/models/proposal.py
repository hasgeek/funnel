# -*- coding: utf-8 -*-

from . import db, TimestampMixin, UuidMixin, BaseScopedIdNameMixin, MarkdownColumn, JsonDict, CoordinatesMixin, UrlType
from .user import User
from .project import Project
from .section import Section
from .commentvote import Commentset, Voteset, SET_TYPE
from coaster.utils import LabeledEnum
from coaster.sqlalchemy import SqlSplitIdComparator, StateManager, with_roles
from baseframe import __
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.utils import cached_property
from ..util import geonameid_from_location

__all__ = ['PROPOSAL_STATE', 'Proposal', 'ProposalRedirect']

_marker = object()


# --- Constants ------------------------------------------------------------------

class PROPOSAL_STATE(LabeledEnum):
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
    SHORTLISTED_FOR_REHEARSAL = (9, 'shortlisted_for_rehearsal', __("Shortlisted for rehearsal"))
    REHEARSAL = (10, 'rehearsal', __("Rehearsal ongoing"))

    # Groups
    CONFIRMABLE = {WAITLISTED, UNDER_EVALUATION, SHORTLISTED, SHORTLISTED_FOR_REHEARSAL, REHEARSAL}
    REJECTABLE = {WAITLISTED, UNDER_EVALUATION, SHORTLISTED, SHORTLISTED_FOR_REHEARSAL, REHEARSAL}
    WAITLISTABLE = {CONFIRMED, UNDER_EVALUATION}
    EVALUATEABLE = {SUBMITTED, AWAITING_DETAILS}
    DELETABLE = {DRAFT, SUBMITTED, CONFIRMED, WAITLISTED, REJECTED, AWAITING_DETAILS, UNDER_EVALUATION}
    CANCELLABLE = {DRAFT, SUBMITTED, CONFIRMED, WAITLISTED, REJECTED, AWAITING_DETAILS, UNDER_EVALUATION}
    UNDO_TO_SUBMITTED = {AWAITING_DETAILS, UNDER_EVALUATION, REJECTED}
    # SHORLISTABLE = {SUBMITTED, AWAITING_DETAILS, UNDER_EVALUATION}


# --- Models ------------------------------------------------------------------

class ProposalFormData(object):
    """
    Form data access helper for custom fields
    """
    def __init__(self, proposal):
        self.__dict__['proposal'] = proposal
        self.__dict__['data'] = proposal.data

    def __getattr__(self, attr, default=_marker):
        if attr in self.proposal.__invalid_fields__ or attr.startswith('_'):
            raise AttributeError("Invalid attribute: %s" % attr)

        if default is _marker:
            try:
                if hasattr(self.proposal, attr):
                    return getattr(self.proposal, attr)
                return self.data[attr]
            except KeyError:
                raise AttributeError(attr)
        else:
            if hasattr(self.proposal, attr):
                return getattr(self.proposal, attr, default)
            return self.data.get(attr, default)

    def __setattr__(self, attr, value):
        if attr in self.proposal.__invalid_fields__ or attr.startswith('_'):
            raise AttributeError("Invalid attribute: %s" % attr)

        if hasattr(self.proposal, attr):
            if attr in self.proposal.__valid_fields__:
                setattr(self.proposal, attr, value)
            else:
                raise AttributeError("Cannot set attribute: %s" % attr)
        else:
            self.data[attr] = value


class Proposal(UuidMixin, BaseScopedIdNameMixin, CoordinatesMixin, db.Model):
    __tablename__ = 'proposal'

    user_id = db.Column(None, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('proposals', cascade="all, delete-orphan"))

    speaker_id = db.Column(None, db.ForeignKey('user.id'), nullable=True)
    speaker = db.relationship(User, primaryjoin=speaker_id == User.id, lazy='joined',
        backref=db.backref('speaker_at', cascade="all"))

    email = db.Column(db.Unicode(80), nullable=True)
    phone = db.Column(db.Unicode(80), nullable=True)
    bio = MarkdownColumn('bio', nullable=True)
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project, primaryjoin=project_id == Project.id,
        backref=db.backref('proposals', cascade="all, delete-orphan", lazy='dynamic'))
    parent = db.synonym('project')

    section_id = db.Column(None, db.ForeignKey('section.id'), nullable=True)
    section = db.relationship(Section, primaryjoin=section_id == Section.id,
        backref="proposals")
    objective = MarkdownColumn('objective', nullable=True)
    part_a = db.synonym('objective')
    session_type = db.Column(db.Unicode(40), nullable=True)
    technical_level = db.Column(db.Unicode(40), nullable=True)
    description = MarkdownColumn('description', nullable=True)
    part_b = db.synonym('description')
    requirements = MarkdownColumn('requirements', nullable=True)
    slides = db.Column(UrlType, nullable=True)
    preview_video = db.Column(UrlType, default=u'', nullable=True)
    links = db.Column(db.Text, default=u'', nullable=True)

    _state = db.Column('state', db.Integer, StateManager.check_constraint('state', PROPOSAL_STATE),
        default=PROPOSAL_STATE.SUBMITTED, nullable=False)
    state = StateManager('_state', PROPOSAL_STATE, doc="Current state of the proposal")

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False, lazy='joined',
        cascade='all, delete-orphan', single_parent=True)

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(Commentset, uselist=False, lazy='joined',
        cascade='all, delete-orphan', single_parent=True)

    edited_at = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.Unicode(80), nullable=False)

    # Additional form data
    data = db.Column(JsonDict, nullable=False, server_default='{}')

    __table_args__ = (db.UniqueConstraint('project_id', 'url_id'),)

    # XXX: The following two may overlap. Reconsider whether both are needed

    # Allow these fields to be set on the proposal by custom forms
    __valid_fields__ = ('title', 'speaker', 'speaking', 'email', 'phone', 'bio', 'section', 'objective', 'session_type',
        'technical_level', 'description', 'requirements', 'slides', 'preview_video', 'links', 'location',
        'latitude', 'longitude', 'coordinates')
    # Never allow these fields to be set on the proposal or proposal.data by custom forms
    __invalid_fields__ = ('id', 'name', 'url_id', 'user_id', 'user', 'speaker_id', 'project_id',
        'project', 'parent', 'voteset_id', 'voteset', 'commentset_id', 'commentset', 'edited_at', 'data')

    __roles__ = {
        'all': {
            'read': {
                'title', 'speaker', 'speaking', 'bio', 'section', 'objective', 'session_type',
                'technical_level', 'description', 'requirements', 'slides', 'preview_video', 'links', 'location',
                'latitude', 'longitude', 'coordinates'
                },
            'call': {
                'url_for'
                }
            },
        'reviewer': {
            'read': {
                'email', 'phone'
                }
            }
        }

    def __init__(self, **kwargs):
        super(Proposal, self).__init__(**kwargs)
        self.voteset = Voteset(type=SET_TYPE.PROPOSAL)
        self.commentset = Commentset(type=SET_TYPE.PROPOSAL)

    def __repr__(self):
        return u'<Proposal "{proposal}" in project "{project}" by "{user}">'.format(
            proposal=self.title, project=self.project.title, user=self.owner.fullname)

    @db.validates('project')
    def _validate_project(self, key, value):
        if not value:
            raise ValueError(value)

        if value != self.project and self.project is not None:
            redirect = ProposalRedirect.query.get((self.project_id, self.url_id))
            if redirect is None:
                redirect = ProposalRedirect(project=self.project, url_id=self.url_id, proposal=self)
                db.session.add(redirect)
            else:
                redirect.proposal = self
        return value

    # State transitions
    state.add_conditional_state('SCHEDULED', state.CONFIRMED, lambda proposal: proposal.session is not None and proposal.session.scheduled, label=('scheduled', __("Confirmed & Scheduled")))

    @with_roles(call={'speaker', 'proposer'})
    @state.transition(state.AWAITING_DETAILS, state.DRAFT, title=__("Draft"), message=__("This proposal has been withdrawn"), type='danger')
    def withdraw(self):
        pass

    @with_roles(call={'speaker', 'proposer'})
    @state.transition(state.DRAFT, state.SUBMITTED, title=__("Submit"), message=__("This proposal has been submitted"), type='success')
    def submit(self):
        pass

    @with_roles(call={'admin', 'reviewer'})
    @state.transition(state.UNDO_TO_SUBMITTED, state.SUBMITTED, title=__("Send Back to Submitted"), message=__("This proposal has been submitted"), type='danger')
    def undo_to_submitted(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.CONFIRMABLE, state.CONFIRMED, title=__("Confirm"), message=__("This proposal has been confirmed"), type='success')
    def confirm(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.CONFIRMED, state.SUBMITTED, title=__("Unconfirm"), message=__("This proposal is no longer confirmed"), type='danger')
    def unconfirm(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.WAITLISTABLE, state.WAITLISTED, title=__("Waitlist"), message=__("This proposal has been waitlisted"), type='primary')
    def waitlist(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.REJECTABLE, state.REJECTED, title=__("Reject"), message=__("This proposal has been rejected"), type='danger')
    def reject(self):
        pass

    @with_roles(call={'speaker', 'proposer'})
    @state.transition(state.CANCELLABLE, state.CANCELLED, title=__("Cancel"), message=__("This proposal has been cancelled"), type='danger')
    def cancel(self):
        pass

    @with_roles(call={'admin', 'reviewer'})
    @state.transition(state.SUBMITTED, state.AWAITING_DETAILS, title=__("Awaiting details"), message=__("Awaiting details for this proposal"), type='primary')
    def awaiting_details(self):
        pass

    @with_roles(call={'admin', 'reviewer'})
    @state.transition(state.EVALUATEABLE, state.UNDER_EVALUATION, title=__("Under evaluation"), message=__("This proposal has been put under evaluation"), type='success')
    def under_evaluation(self):
        pass

    @with_roles(call={'speaker', 'proposer'})
    @state.transition(state.DELETABLE, state.DELETED, title=__("Delete"), message=__("This proposal has been deleted"), type='danger')
    def delete(self):
        pass

    # These 3 transitions are not in the editorial workflow anymore - Feb 23 2018

    # @with_roles(call={'admin'})
    # @state.transition(state.SUBMITTED, state.SHORTLISTED, title=__("Shortlist"), message=__("This proposal has been shortlisted"), type='success')
    # def shortlist(self):
    #     pass

    # @with_roles(call={'admin'})
    # @state.transition(state.SHORLISTABLE, state.SHORTLISTED_FOR_REHEARSAL, title=__("Shortlist for rehearsal"), message=__("This proposal has been shortlisted for rehearsal"), type='success')
    # def shortlist_for_rehearsal(self):
    #     pass

    # @with_roles(call={'admin'})
    # @state.transition(state.SHORTLISTED_FOR_REHEARSAL, state.REHEARSAL, title=__("Rehearsal ongoing"), message=__("Rehearsal is now ongoing for this proposal"), type='success')
    # def rehearsal_ongoing(self):
    #     pass

    @with_roles(call={'admin'})
    def move_to(self, project):
        """
        Move to a new project and reset the url_id
        """
        self.project = project
        self.url_id = None
        self.make_id()

    @property
    def formdata(self):
        return ProposalFormData(self)

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

    @property
    def datetime(self):
        return self.created_at  # Until proposals have a workflow-driven datetime

    @cached_property
    def has_outstation_speaker(self):
        """
        Returns True iff the location can be geocoded and is found to be different
        compared to the project's location.
        """
        geonameid = geonameid_from_location(self.location)
        return bool(geonameid) and self.project.location_geonameid.isdisjoint(geonameid)

    def getnext(self):
        return Proposal.query.filter(Proposal.project == self.project).filter(
            Proposal.id != self.id).filter(Proposal._state == self.state.value).filter(
                Proposal.created_at < self.created_at).order_by(db.desc('created_at')).first()

    def getprev(self):
        return Proposal.query.filter(Proposal.project == self.project).filter(
            Proposal.id != self.id).filter(Proposal._state == self.state.value).filter(
                Proposal.created_at > self.created_at).order_by('created_at').first()

    def votes_count(self):
        return len(self.voteset.votes)

    def permissions(self, user, inherited=None):
        perms = super(Proposal, self).permissions(user, inherited)
        if user is not None:
            perms.update([
                'vote_proposal',
                'new_comment',
                'vote_comment',
                ])
            if user == self.owner:
                perms.update([
                    'view-proposal',
                    'edit-proposal',
                    'delete-proposal',  # FIXME: Prevent deletion of confirmed proposals
                    'submit-proposal',  # For workflows, to confirm the form is ready for submission (from draft state)
                    'transfer-proposal',
                    ])
                if self.speaker != self.user:
                    perms.add('decline-proposal')  # Decline speaking
        return perms

    # Roles

    def roles_for(self, actor=None, anchors=()):
        roles = super(Proposal, self).roles_for(actor, anchors)
        if self.speaker and self.speaker == actor:
            roles.add('speaker')
        if self.user and self.user == actor:
            roles.add('proposer')
        roles.update(self.project.roles_for(actor, anchors))
        if self.state.DRAFT and 'reader' in roles:
            roles.remove('reader')  # https://github.com/hasgeek/funnel/pull/220#discussion_r168724439
        return roles


class ProposalRedirect(TimestampMixin, db.Model):
    __tablename__ = 'proposal_redirect'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False, primary_key=True)
    project = db.relationship(Project, primaryjoin=project_id == Project.id,
        backref=db.backref('proposal_redirects', cascade="all, delete-orphan"))
    parent = db.synonym('project')
    url_id = db.Column(db.Integer, nullable=False, primary_key=True)

    proposal_id = db.Column(None, db.ForeignKey('proposal.id', ondelete='SET NULL'), nullable=True)
    proposal = db.relationship(Proposal, backref='redirects')

    @hybrid_property
    def url_id_name(self):
        """
        Returns a URL name that is just :attr:`url_id`. This property is also
        available as :attr:`url_name` for legacy reasons. This property will
        likely never be called directly on an instance. It exists for the SQL
        comparator that will be called to load the instance.
        """
        return unicode(self.url_id)

    @url_id_name.comparator
    def url_id_name(cls):
        return SqlSplitIdComparator(cls.url_id, splitindex=0)

    url_name = url_id_name  # Legacy name

    def __repr__(self):
        return '<ProposalRedirect %s/%s/%s: %s/%s/%s>' % (
            self.project.profile.name, self.project.name, self.url_id,
            self.proposal.project.profile.name if self.proposal else "(none)",
            self.proposal.project.name if self.proposal else "(none)",
            self.proposal.url_id if self.proposal else "(none)")

    def redirect_view_args(self):
        if self.proposal:
            return {
                'profile': self.proposal.project.profile.name,
                'project': self.proposal.project.name,
                'proposal': self.proposal.url_name
                }
        else:
            return {}
