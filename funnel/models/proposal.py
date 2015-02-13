# -*- coding: utf-8 -*-

from flask import url_for, abort
from . import db, TimestampMixin, BaseScopedIdNameMixin, MarkdownColumn, JsonDict, CoordinatesMixin
from .user import User
from .space import ProposalSpace
from .section import ProposalSpaceSection
from .commentvote import CommentSpace, VoteSpace, SPACETYPE
from coaster.utils import LabeledEnum
from baseframe import __
from sqlalchemy.ext.hybrid import hybrid_property
from flask import request
from pytz import timezone, utc, UnknownTimeZoneError

__all__ = ['PROPOSALSTATUS', 'Proposal', 'ProposalRedirect']

_marker = object()

# --- Constants ------------------------------------------------------------------


class PROPOSALSTATUS(LabeledEnum):
    # Draft-state for future use, so people can save their proposals and submit only when ready
    DRAFT = (0, __("Draft"))
    SUBMITTED = (1, __("Submitted"))
    CONFIRMED = (2, __("Confirmed"))
    WAITLISTED = (3, __("Waitlisted"))
    SHORTLISTED = (4, __("Shortlisted"))
    REJECTED = (5, __("Rejected"))
    CANCELLED = (6, __("Cancelled"))


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
    session_type = db.Column(db.Unicode(40), nullable=True)
    technical_level = db.Column(db.Unicode(40), nullable=True)
    description = MarkdownColumn('description', nullable=True)
    requirements = MarkdownColumn('requirements', nullable=True)
    slides = db.Column(db.Unicode(250), nullable=True)
    preview_video = db.Column(db.Unicode(250), default=u'', nullable=True)
    links = db.Column(db.Text, default=u'', nullable=True)
    status = db.Column(db.Integer, default=PROPOSALSTATUS.SUBMITTED, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False, cascade='all, delete-orphan', single_parent=True)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False, cascade='all, delete-orphan', single_parent=True)

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
        return u'<Proposal "{proposal}" in space "{space}" by "{user}">'.format(proposal=self.title, space=self.proposal_space.title, user=self.owner.fullname)

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

    @property
    def status_title(self):
        return PROPOSALSTATUS[self.status]

    @hybrid_property
    def confirmed(self):
        return self.status == PROPOSALSTATUS.CONFIRMED

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
        groupuserids = dict([(group.name, [user.userid for user in group.users])
            for group in self.proposal_space.usergroups])
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
        elif action == 'status':
            return url_for('proposal_status', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, **kwargs)
        elif action == 'move-to':
            return url_for('proposal_moveto', profile=self.proposal_space.profile.name, space=self.proposal_space.name, proposal=self.url_name, _external=_external, target="%s/%s" % (kwargs['target'].profile.name, kwargs['target'].name))


class ProposalRedirect(TimestampMixin, db.Model):
    __tablename__ = "proposal_redirect"

    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False, primary_key=True)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('proposal_redirects', cascade="all, delete-orphan"))
    parent = db.synonym('proposal_space')
    url_id = db.Column(db.Integer, nullable=False, primary_key=True)
    url_id_attr = 'url_id'

    proposal_id = db.Column(None, db.ForeignKey('proposal.id', ondelete='SET NULL'), nullable=True)
    proposal = db.relationship(Proposal, backref='redirects')

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
