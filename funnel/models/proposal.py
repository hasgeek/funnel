# -*- coding: utf-8 -*-

from flask import url_for, abort
from . import db, TimestampMixin, BaseScopedIdNameMixin, MarkdownColumn, JsonDict, CoordinatesMixin
from .user import User
from .space import ProposalSpace
from .section import ProposalSpaceSection
from .commentvote import CommentSpace, VoteSpace, SPACETYPE
from coaster.utils import LabeledEnum
from coaster.sqlalchemy import SqlSplitIdComparator, StateManager, with_roles
from baseframe import __
from sqlalchemy.ext.hybrid import hybrid_property
from flask import request
from pytz import timezone, utc, UnknownTimeZoneError
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
    SHORTLISTED = (4, 'shortlisted', __("Shortlisted"))
    REJECTED = (5, 'rejected', __("Rejected"))
    CANCELLED = (6, 'cancelled', __("Cancelled"))

    AWAITING_DETAILS = (7, 'awaiting_details', __("Awaiting details"))
    UNDER_EVALUATION = (8, 'under_evaluation', __("Under evaluation"))
    SHORTLISTED_FOR_REHEARSAL = (9, 'shortlisted_for_rehearsal', __("Shortlisted for rehearsal"))
    REHEARSAL = (10, 'rehearsal', __("Rehearsal ongoing"))

    DELETED = (11, 'deleted', __("Deleted"))

    CONFIRMABLE = {SUBMITTED, WAITLISTED, SHORTLISTED, REHEARSAL}
    WAITLISTABLE = {SUBMITTED, CONFIRMED, SHORTLISTED, REJECTED, CANCELLED}
    EVALUATEABLE = {SUBMITTED, AWAITING_DETAILS}
    SHORLISTABLE = {SUBMITTED, AWAITING_DETAILS, UNDER_EVALUATION}
    DELETABLE = {DRAFT, SUBMITTED}

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


class Proposal(BaseScopedIdNameMixin, CoordinatesMixin, db.Model):
    __tablename__ = 'proposal'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('proposals', cascade="all, delete-orphan"))

    speaker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    speaker = db.relationship(User, primaryjoin=speaker_id == User.id,
        backref=db.backref('speaker_at', cascade="all"))

    email = db.Column(db.Unicode(80), nullable=True)
    phone = db.Column(db.Unicode(80), nullable=True)
    bio = MarkdownColumn('bio', nullable=True)
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('proposals', cascade="all, delete-orphan", lazy='dynamic'))
    parent = db.synonym('proposal_space')

    section_id = db.Column(db.Integer, db.ForeignKey('proposal_space_section.id'), nullable=True)
    section = db.relationship(ProposalSpaceSection, primaryjoin=section_id == ProposalSpaceSection.id,
        backref="proposals")
    objective = MarkdownColumn('objective', nullable=True)
    part_a = db.synonym('objective')
    session_type = db.Column(db.Unicode(40), nullable=True)
    technical_level = db.Column(db.Unicode(40), nullable=True)
    description = MarkdownColumn('description', nullable=True)
    part_b = db.synonym('description')
    requirements = MarkdownColumn('requirements', nullable=True)
    slides = db.Column(db.Unicode(250), nullable=True)
    preview_video = db.Column(db.Unicode(250), default=u'', nullable=True)
    links = db.Column(db.Text, default=u'', nullable=True)

    _state = db.Column('status', db.Integer, StateManager.check_constraint('status', PROPOSAL_STATE),
        default=PROPOSAL_STATE.SUBMITTED, nullable=False)
    state = StateManager('_state', PROPOSAL_STATE, doc="Current state of the proposal")

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False,
                            cascade='all, delete-orphan', single_parent=True)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False,
                               cascade='all, delete-orphan', single_parent=True)

    edited_at = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.Unicode(80), nullable=False)

    # Additional form data
    data = db.Column(JsonDict, nullable=False, server_default='{}')

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'url_id'),)

    # XXX: The following two may overlap. Reconsider whether both are needed

    # Allow these fields to be set on the proposal by custom forms
    __valid_fields__ = ('title', 'speaker', 'speaking', 'email', 'phone', 'bio', 'section', 'objective', 'session_type',
        'technical_level', 'description', 'requirements', 'slides', 'preview_video', 'links', 'location',
        'latitude', 'longitude', 'coordinates')
    # Never allow these fields to be set on the proposal or proposal.data by custom forms
    __invalid_fields__ = ('id', 'name', 'url_id', 'user_id', 'user', 'speaker_id', 'proposal_space_id',
        'proposal_space', 'parent', 'votes_id', 'votes', 'comments_id', 'comments', 'edited_at', 'data')

    def __init__(self, **kwargs):
        super(Proposal, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSAL)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSAL)

    def __repr__(self):
        return u'<Proposal "{proposal}" in space "{space}" by "{user}">'.format(
            proposal=self.title, space=self.proposal_space.title, user=self.owner.fullname)

    @db.validates('proposal_space')
    def _validate_proposal_space(self, key, value):
        if not value:
            raise ValueError(value)

        if value != self.proposal_space and self.proposal_space is not None:
            redirect = ProposalRedirect.query.get((self.proposal_space_id, self.url_id))
            if redirect is None:
                redirect = ProposalRedirect(proposal_space=self.proposal_space, url_id=self.url_id, proposal=self)
                db.session.add(redirect)
            else:
                redirect.proposal = self
        return value

    # State transitions
    state.add_conditional_state('SCHEDULED', state.CONFIRMED, lambda proposal: proposal.session is not None, label=__("Confirmed & Scheduled"))

    @with_roles(call={'speaker', 'proposer'})
    @state.transition(state.AWAITING_DETAILS, state.DRAFT, title=__("Draft"), message=__("This proposal has been withdrawn"), type='danger')
    def withdraw(self):
        pass

    @with_roles(call={'speaker', 'proposer'})
    @state.transition(state.DRAFT, state.SUBMITTED, title=__("Submit"), message=__("This proposal has been submitted"), type='success')
    def submit(self):
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
    @state.transition(state.SUBMITTED, state.SHORTLISTED, title=__("Shortlist"), message=__("This proposal has been shortlisted"), type='success')
    def shortlist(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.SUBMITTED, state.REJECTED, title=__("Reject"), message=__("This proposal has been rejected"), type='danger')
    def reject(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.SUBMITTED, state.CANCELLED, title=__("Cancel"), message=__("This proposal has been cancelled"), type='danger')
    def cancel(self):
        pass

    @with_roles(call={'reviewer'})
    @state.transition(state.SUBMITTED, state.AWAITING_DETAILS, title=__("Awaiting details"), message=__("Awaiting details for this proposal"), type='primary')
    def awaiting_details(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.EVALUATEABLE, state.UNDER_EVALUATION, title=__("Under evaluation"), message=__("This proposal has been put under evaluation"), type='success')
    def under_evaluation(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.SHORLISTABLE, state.SHORTLISTED_FOR_REHEARSAL, title=__("Shortlist for rehearsal"), message=__("This proposal has been shortlisted for rehearsal"), type='success')
    def shortlist_for_rehearsal(self):
        pass

    @with_roles(call={'admin'})
    @state.transition(state.SHORTLISTED_FOR_REHEARSAL, state.REHEARSAL, title=__("Rehearsal ongoing"), message=__("Rehearsal is now ongoing for this proposal"), type='success')
    def rehearsal_ongoing(self):
        pass

    @with_roles(call={'admin', 'speaker', 'proposer'})
    @state.transition(state.DELETABLE, state.DELETED, title=__("Delete"), message=__("This proposal has been deleted"), type='danger')
    def delete(self):
        pass

    @with_roles(call={'admin'})
    def move_to(self, space):
        """
        Move to a new proposal space and reset the url_id
        """
        self.proposal_space = space
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
        compared to the proposal space's location.
        """
        geonameid = geonameid_from_location(self.location)
        return bool(geonameid) and self.proposal_space.location_geonameid.isdisjoint(geonameid)

    def getnext(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
                Proposal.created_at < self.created_at).order_by(db.desc('created_at')).first()

    def getprev(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
                Proposal.created_at > self.created_at).order_by('created_at').first()

    def votes_count(self):
        return len(self.votes.votes)

    def votes_by_group(self):
        votes_groups = dict([(group.name, 0) for group in self.proposal_space.usergroups])
        groupuserids = dict([(group.name, [user.userid for user in group.users]) for group in self.proposal_space.usergroups])
        for vote in self.votes.votes:
            for groupname, userids in groupuserids.items():
                if vote.user.userid in userids:
                    votes_groups[groupname] += -1 if vote.votedown else +1
        return votes_groups

    def votes_by_date(self):
        if 'tz' in request.args:
            try:
                tz = timezone(request.args['tz'])
            except UnknownTimeZoneError:
                abort(400)
        else:
            tz = None
        votes_bydate = dict([(group.name, {}) for group in self.proposal_space.usergroups])
        groupuserids = dict([(group.name, [user.userid for user in group.users])
            for group in self.proposal_space.usergroups])
        for vote in self.votes.votes:
            for groupname, userids in groupuserids.items():
                if vote.user.userid in userids:
                    if tz:
                        date = tz.normalize(vote.updated_at.replace(tzinfo=utc).astimezone(tz)).strftime('%Y-%m-%d')
                    else:
                        date = vote.updated_at.strftime('%Y-%m-%d')
                    votes_bydate[groupname].setdefault(date, 0)
                    votes_bydate[groupname][date] += -1 if vote.votedown else +1
        return votes_bydate

    def permissions(self, user, inherited=None):
        perms = super(Proposal, self).permissions(user, inherited)
        if user is not None:
            perms.update([
                'vote-proposal',
                'new-comment',
                'vote-comment',
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
        roles.update(self.proposal_space.roles_for(actor, anchors))
        if self.state.DRAFT and 'reader' in roles:
            roles.remove('reader')  # https://github.com/hasgeek/funnel/pull/220#discussion_r168724439
        return roles

    def url_for(self, action='view', _external=False, **kwargs):
        if action == 'view':
            return url_for('proposal_view', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'json':
            return url_for('proposal_json', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'edit':
            return url_for('proposal_edit', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'delete':
            return url_for('proposal_delete', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'voteup':
            return url_for('proposal_voteup', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'votedown':
            return url_for('proposal_votedown', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'votecancel':
            return url_for('proposal_cancelvote', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'next':
            return url_for('proposal_next', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'prev':
            return url_for('proposal_prev', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'schedule':
            return url_for('proposal_schedule', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'transition':
            return url_for('proposal_transition', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'move-to':
            return url_for('proposal_moveto', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)


class ProposalRedirect(TimestampMixin, db.Model):
    __tablename__ = 'proposal_redirect'

    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('proposal_redirects', cascade="all, delete-orphan"))
    parent = db.synonym('proposal_space')
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
            self.proposal_space.profile.name, self.proposal_space.name, self.url_id,
            self.proposal.proposal_space.profile.name if self.proposal else "(none)",
            self.proposal.proposal_space.name if self.proposal else "(none)",
            self.proposal.url_id if self.proposal else "(none)")

    def redirect_view_args(self):
        if self.proposal:
            return {
                'profile': self.proposal.proposal_space.profile.name,
                'space': self.proposal.proposal_space.name,
                'proposal': self.proposal.url_name
                }
        else:
            return {}
