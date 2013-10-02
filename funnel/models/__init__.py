# -*- coding: utf-8 -*-

from flask import url_for
from flask.ext.lastuser.sqlalchemy import UserBase
from coaster.sqlalchemy import BaseMixin, BaseNameMixin, BaseScopedNameMixin, BaseIdNameMixin, MarkdownColumn
from coaster.db import db

__all__ = ['db', 'SPACESTATUS', 'User', 'ProposalSpace', 'ProposalSpaceSection', 'Proposal',
           'VoteSpace', 'Vote', 'CommentSpace', 'Comment', 'UserGroup', 'FEEDBACK_AUTH_TYPE', 'ProposalFeedback']


# --- Constants ---------------------------------------------------------------

class SPACESTATUS:
    DRAFT = 0
    SUBMISSIONS = 1
    VOTING = 2
    JURY = 3
    FEEDBACK = 4
    CLOSED = 5
    WITHDRAWN = 6


class COMMENTSTATUS:
    PUBLIC = 0
    SCREENED = 1
    HIDDEN = 2
    SPAM = 3
    DELETED = 4  # For when there are children to be preserved


# What is this VoteSpace or CommentSpace attached to?
class SPACETYPE:
    PROPOSALSPACE = 0
    PROPOSALSPACESECTION = 1
    PROPOSAL = 2
    COMMENT = 3


class FEEDBACK_AUTH_TYPE:
    NOAUTH = 0
    HGAUTH = 1


# --- Models ------------------------------------------------------------------

class User(UserBase, db.Model):
    __tablename__ = 'user'
    description = db.Column(db.Text, default=u'', nullable=False)


class VoteSpace(BaseMixin, db.Model):
    __tablename__ = 'votespace'
    type = db.Column(db.Integer, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, **kwargs):
        super(VoteSpace, self).__init__(**kwargs)
        self.count = 0

    def vote(self, user, votedown=False):
        voteob = Vote.query.filter_by(user=user, votespace=self).first()
        if not voteob:
            voteob = Vote(user=user, votespace=self, votedown=votedown)
            self.count += 1 if not votedown else -1
            db.session.add(voteob)
        else:
            if voteob.votedown != votedown:
                self.count += 2 if not votedown else -2
            voteob.votedown = votedown
        return voteob

    def cancelvote(self, user):
        voteob = Vote.query.filter_by(user=user, votespace=self).first()
        if voteob:
            self.count += 1 if voteob.votedown else -1
            db.session.delete(voteob)

    def getvote(self, user):
        return Vote.query.filter_by(user=user, votespace=self).first()


class Vote(BaseMixin, db.Model):
    __tablename__ = 'vote'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('votes', cascade="all, delete-orphan"))
    votespace_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votespace = db.relationship(VoteSpace, primaryjoin=votespace_id == VoteSpace.id,
        backref=db.backref('votes', cascade="all, delete-orphan"))
    votedown = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "votespace_id"), {})


class CommentSpace(BaseMixin, db.Model):
    __tablename__ = 'commentspace'
    type = db.Column(db.Integer, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)

    def __init__(self, **kwargs):
        super(CommentSpace, self).__init__(**kwargs)
        self.count = 0


class Comment(BaseMixin, db.Model):
    __tablename__ = 'comment'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('comments', cascade="all"))
    commentspace_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    commentspace = db.relationship(CommentSpace, primaryjoin=commentspace_id == CommentSpace.id,
        backref=db.backref('comments', cascade="all, delete-orphan"))

    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    children = db.relationship("Comment", backref=db.backref("parent", remote_side="Comment.id"))

    message = MarkdownColumn('message', nullable=False)

    status = db.Column(db.Integer, default=0, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    edited_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super(Comment, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.COMMENT)

    def delete(self):
        """
        Delete this comment.
        """
        if len(self.children) > 0:
            self.status = COMMENTSTATUS.DELETED
            self.user = None
            self.message = ''
        else:
            if self.parent and self.parent.is_deleted:
                # If the parent is deleted, ask it to reconsider removing itself
                parent = self.parent
                parent.children.remove(self)
                db.session.delete(self)
                parent.delete()
            else:
                db.session.delete(self)

    @property
    def is_deleted(self):
        return self.status == COMMENTSTATUS.DELETED

    def sorted_children(self):
        return sorted(self.children, key=lambda child: child.votes.count)

    def permissions(self, user, inherited=None):
        perms = super(Comment, self).permissions(user, inherited)
        if user is not None and user == self.user:
            perms.update([
                'edit-comment',
                'delete-comment'
                ])
        return perms

    def url_for(self, action='view', proposal=None, _external=False):
        if action == 'view':
            return proposal.url_for() + "#c%d" % self.id
        elif action == 'json':
            return url_for('comment_json', space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
        elif action == 'voteup':
            return url_for('comment_voteup', space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
        elif action == 'votedown':
            return url_for('comment_votedown', space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)
        elif action == 'cancelvote':
            return url_for('comment_cancelvote', space=proposal.proposal_space.name, proposal=proposal.url_name,
                comment=self.id, _external=_external)


class ProposalSpace(BaseNameMixin, db.Model):
    __tablename__ = 'proposal_space'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref=db.backref('spaces', cascade="all, delete-orphan"))
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = MarkdownColumn('description', default=u'', nullable=False)
    datelocation = db.Column(db.Unicode(50), default=u'', nullable=False)
    date = db.Column(db.Date, nullable=True)
    website = db.Column(db.Unicode(250), nullable=True)
    status = db.Column(db.Integer, default=SPACESTATUS.DRAFT, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    def __init__(self, **kwargs):
        super(ProposalSpace, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACE)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACE)

    def permissions(self, user, inherited=None):
        perms = super(ProposalSpace, self).permissions(user, inherited)
        perms.add('view')
        if user is not None:
            if self.status == SPACESTATUS.SUBMISSIONS:
                perms.add('new-proposal')
            if user == self.user:
                perms.update([
                    'edit-space',
                    'delete-space',
                    'view-section',
                    'new-section',
                    'view-usergroup',
                    'new-usergroup',
                    'confirm-proposal',
                    ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('space_view', space=self.name, _external=_external)
        elif action == 'json':
            return url_for('space_view_json', space=self.name, _external=_external)
        elif action == 'csv':
            return url_for('space_view_csv', space=self.name, _external=_external)
        elif action == 'edit':
            return url_for('space_edit', space=self.name, _external=_external)
        elif action == 'sections':
            return url_for('section_list', space=self.name, _external=_external)
        elif action == 'new-section':
            return url_for('section_new', space=self.name, _external=_external)
        elif action == 'usergroups':
            return url_for('usergroup_list', space=self.name, _external=_external)
        elif action == 'new-usergroup':
            return url_for('usergroup_new', space=self.name, _external=_external)
        elif action == 'new-proposal':
            return url_for('proposal_new', space=self.name, _external=_external)


class ProposalSpaceSection(BaseScopedNameMixin, db.Model):
    __tablename__ = 'proposal_space_section'
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('sections', cascade="all, delete-orphan"))
    parent = db.synonym('proposal_space')

    description = db.Column(db.Text, default=u'', nullable=False)
    public = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("proposal_space_id", "name"), {})

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    def __init__(self, **kwargs):
        super(ProposalSpaceSection, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSALSPACESECTION)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSALSPACESECTION)

    def permissions(self, user, inherited=None):
        perms = super(ProposalSpaceSection, self).permissions(user, inherited)
        if user is not None and user == self.proposal_space.user:
            perms.update([
                'edit-section',
                'delete-section',
                ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('section_view', space=self.proposal_space.name, section=self.name, _external=_external)
        elif action == 'edit':
            return url_for('section_edit', space=self.proposal_space.name, section=self.name, _external=_external)
        elif action == 'delete':
            return url_for('section_delete', space=self.proposal_space.name, section=self.name, _external=_external)
        elif action == 'usergroups':
            return url_for('usergroup_list', space=self.proposal_space.name, section=self.name, _external=_external)


class Proposal(BaseIdNameMixin, db.Model):
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
        backref=db.backref('proposals', cascade="all, delete-orphan"))
    section_id = db.Column(db.Integer, db.ForeignKey('proposal_space_section.id'), nullable=True)
    section = db.relationship(ProposalSpaceSection, primaryjoin=section_id == ProposalSpaceSection.id,
        backref="proposals")
    objective = MarkdownColumn('objective', nullable=False)
    session_type = db.Column(db.Unicode(40), nullable=False, default=u'')
    technical_level = db.Column(db.Unicode(40), nullable=False)
    description = MarkdownColumn('description', nullable=False)
    requirements = MarkdownColumn('requirements', nullable=False)
    slides = db.Column(db.Unicode(250), default=u'', nullable=False)
    links = db.Column(db.Text, default=u'', nullable=False)
    status = db.Column(db.Integer, default=0, nullable=False)
    confirmed = db.Column(db.Boolean, default=False, nullable=False)

    votes_id = db.Column(db.Integer, db.ForeignKey('votespace.id'), nullable=False)
    votes = db.relationship(VoteSpace, uselist=False)

    comments_id = db.Column(db.Integer, db.ForeignKey('commentspace.id'), nullable=False)
    comments = db.relationship(CommentSpace, uselist=False)

    edited_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super(Proposal, self).__init__(**kwargs)
        self.votes = VoteSpace(type=SPACETYPE.PROPOSAL)
        self.comments = CommentSpace(type=SPACETYPE.PROPOSAL)

    def __repr__(self):
        return u'<Proposal "%s" in space "%s" by "%s">' % (self.title, self.proposal_space.title, self.user.fullname)

    def getnext(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
                Proposal.created_at < self.created_at).order_by(db.desc('created_at')).first()

    def getprev(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
                Proposal.created_at > self.created_at).order_by('created_at').first()

    def permissions(self, user, inherited=None):
        perms = super(Proposal, self).permissions(user, inherited)
        if user is not None:
            perms.update([
                'vote-proposal',
                'new-comment',
                'vote-comment',
                ])
            if user == self.user:
                perms.update([
                    'view-proposal',
                    'edit-proposal',
                    'delete-proposal',
                    ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('proposal_view', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'edit':
            return url_for('proposal_edit', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'confirm':
            return url_for('proposal_confirm', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'delete':
            return url_for('proposal_delete', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'voteup':
            return url_for('proposal_voteup', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'votedown':
            return url_for('proposal_votedown', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'cancelvote':
            return url_for('proposal_cancelvote', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'next':
            return url_for('proposal_next', space=self.proposal_space.name, proposal=self.url_name, _external=_external)
        elif action == 'prev':
            return url_for('proposal_prev', space=self.proposal_space.name, proposal=self.url_name, _external=_external)


group_members = db.Table(
    'group_members', db.Model.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('user_group.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    )


class UserGroup(BaseScopedNameMixin, db.Model):
    __tablename__ = 'user_group'
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref=db.backref('usergroups', cascade="all, delete-orphan"))
    parent = db.synonym('proposal_space')
    users = db.relationship(User, secondary=group_members)

    # TODO: Add flags and setup permissions to allow admins access to proposals and votes
    # public = db.Column(Boolean, nullable=False, default=True)
    # admin = db.Column(Boolean, nullable=False, default=False, indexed=True)

    __table_args__ = (db.UniqueConstraint('proposal_space_id', 'name'),)

    def permissions(self, user, inherited=None):
        perms = super(UserGroup, self).permissions(user, inherited)
        if user is not None and user == self.proposal_space.user:
            perms.update([
                'view-usergroup',
                'edit-usergroup',
                'delete-usergroup',
                ])
        return perms

    def url_for(self, action='view', _external=False):
        if action == 'view':
            return url_for('usergroup_view', space=self.proposal_space.name, group=self.name, _external=_external)
        elif action == 'edit':
            return url_for('usergroup_edit', space=self.proposal_space.name, group=self.name, _external=_external)
        elif action == 'delete':
            return url_for('usergroup_delete', space=self.proposal_space.name, group=self.name, _external=_external)


class ProposalFeedback(BaseMixin, db.Model):
    __tablename__ = 'proposal_feedback'
    #: Proposal that we're submitting feedback on
    proposal_id = db.Column(None, db.ForeignKey('proposal.id'), nullable=False)
    proposal = db.relationship(Proposal)
    #: Authentication type (authenticated or not)
    auth_type = db.Column(db.Integer, nullable=False)
    #: Type of identifier for the user
    id_type = db.Column(db.Unicode(80), nullable=False)
    #: User id (of the given type)
    userid = db.Column(db.Unicode(80), nullable=False)
    #: Minimum scale for feedback (x in x-y)
    min_scale = db.Column(db.Integer, nullable=False)
    #: Maximum scale for feedback (y in x-y)
    max_scale = db.Column(db.Integer, nullable=False)
    #: Feedback on the content of the proposal
    content = db.Column(db.Integer, nullable=True)
    #: Feedback on the presentation of the proposal
    presentation = db.Column(db.Integer, nullable=True)

    __table_args__ = (db.UniqueConstraint('proposal_id', 'auth_type', 'id_type', 'userid'),)
