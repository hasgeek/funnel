# -*- coding: utf-8 -*-

from flaskext.sqlalchemy import SQLAlchemy
from flaskext.lastuser.sqlalchemy import UserBase
from app import app
from utils import makename

__all__ = ['db', 'SPACESTATUS', 'User', 'Tag', 'ProposalSpace', 'ProposalSpaceSection', 'Proposal']

db = SQLAlchemy(app)

# --- Constants ---------------------------------------------------------------

class SPACESTATUS:
    DRAFT = 0
    SUBMISSIONS = 1
    VOTING = 2
    JURY = 3
    FEEDBACK = 4
    CLOSED = 5
    REJECTED = 6


# --- Mixins ------------------------------------------------------------------

class BaseMixin(object):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False)


# --- Models ------------------------------------------------------------------

class User(db.Model, UserBase):
    __tablename__ = 'user'
    description = db.Column(db.Text, default='', nullable=False)


class Tag(db.Model, BaseMixin):
    __tablename__ = 'tag'
    name = db.Column(db.Unicode(80), unique=True, nullable=False)
    title = db.Column(db.Unicode(80), unique=True, nullable=False)

    @classmethod
    def gettag(cls, tagname):
        tag = cls.query.filter_by(title=tagname).first()
        if tag:
            return tag
        else:
            name = makename(tagname)
            # Is this name already in use? If yes, return it
            tag = cls.query.filter_by(name=name).first()
            if tag:
                return tag
            else:
                tag = Tag(name=name, title=tagname)
                db.session.add(tag)
                return tag


class ProposalSpace(db.Model, BaseMixin):
    __tablename__ = 'proposal_space'

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref = db.backref('spaces', cascade="all, delete-orphan"))
    name = db.Column(db.Unicode(80), unique=True, nullable=False)
    title = db.Column(db.Unicode(80), nullable=False)
    tagline = db.Column(db.Unicode(250), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    description_html = db.Column(db.Text, default='', nullable=False)
    datelocation = db.Column(db.Unicode(50), default='', nullable=False)
    website = db.Column(db.Unicode(250), nullable=True)
    status = db.Column(db.Integer, default=SPACESTATUS.DRAFT, nullable=False)


class ProposalSpaceSection(db.Model, BaseMixin):
    __tablename__ = 'proposal_space_section'
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref = db.backref('sections', cascade="all, delete-orphan"))

    name = db.Column(db.Unicode(80), nullable=False)
    title = db.Column(db.Unicode(80), nullable=False)
    description = db.Column(db.Text, default='', nullable=False)
    public = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = ( db.UniqueConstraint("proposal_space_id", "name"), {} )


proposal_tags = db.Table(
    'proposal_tags', db.Model.metadata,
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('proposal_id', db.Integer, db.ForeignKey('proposal.id')),
    )


class Proposal(db.Model, BaseMixin):
    __tablename__ = 'proposal'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref= db.backref('proposals', cascade="all, delete-orphan"))
    proposal_space_id = db.Column(db.Integer, db.ForeignKey('proposal_space.id'), nullable=False)
    proposal_space = db.relationship(ProposalSpace, primaryjoin=proposal_space_id == ProposalSpace.id,
        backref = db.backref('proposals', cascade="all, delete-orphan"))
    name = db.Column(db.Unicode(250), nullable=False)
    title = db.Column(db.Unicode(250), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('proposal_space_section.id'), nullable=True)
    section = db.relationship(ProposalSpaceSection, primaryjoin=section_id == ProposalSpaceSection.id,
        backref="proposals")
    objective = db.Column(db.Text, nullable=False)
    objective_html = db.Column(db.Text, nullable=False)
    session_type = db.Column(db.Unicode(40), nullable=False)
    technical_level = db.Column(db.Unicode(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    description_html = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    requirements_html = db.Column(db.Text, nullable=False)
    slides = db.Column(db.Unicode(250), default='', nullable=False)
    links = db.Column(db.Text, default='', nullable=False)
    tags = db.relationship(Tag, secondary=proposal_tags)
    status = db.Column(db.Integer, default=0, nullable=False)

    votecount = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return u'<Proposal "%s" in space "%s" by "%s">' % (self.title, self.proposal_space.title, self.user.fullname)

    @property
    def urlname(self):
        return '%s-%s' % (self.id, self.name)

    def vote(self, user, votedown=False):
        voteob = Vote.query.filter_by(user=user, proposal=self).first()
        if not voteob:
            voteob = Vote(user=user, proposal=self, votedown=votedown)
            self.votecount += 1 if not votedown else -1
            db.session.add(voteob)
        else:
            if voteob.votedown != votedown:
                self.votecount += 2 if not votedown else -2
            voteob.votedown = votedown
        return voteob

    def cancelvote(self, user):
        voteob = Vote.query.filter_by(user=user, proposal=self).first()
        if voteob:
            self.votecount += 1 if voteob.votedown else -1
            db.session.delete(voteob)

    def getvote(self, user):
        return Vote.query.filter_by(user=user, proposal=self).first()

    def getnext(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
            Proposal.created_at > self.created_at).order_by('created_at').first()

    def getprev(self):
        return Proposal.query.filter(Proposal.proposal_space == self.proposal_space).filter(
            Proposal.id != self.id).filter(
            Proposal.created_at < self.created_at).order_by(db.desc('created_at')).first()


class Vote(db.Model, BaseMixin):
    __tablename__ = 'vote'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref= db.backref('votes', cascade="all, delete-orphan"))
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=False)
    proposal = db.relationship(Proposal, primaryjoin=proposal_id == Proposal.id,
        backref = db.backref('votes', cascade="all, delete-orphan"))
    votedown = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = ( db.UniqueConstraint("user_id", "proposal_id"), {} )


class Comment(db.Model, BaseMixin):
    __tablename__ = 'comment'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User, primaryjoin=user_id == User.id,
        backref= db.backref('comments', cascade="all, delete-orphan"))
    proposal_id = db.Column(db.Integer, db.ForeignKey('proposal.id'), nullable=False)
    proposal = db.relationship(Proposal, primaryjoin=proposal_id == Proposal.id,
        backref = db.backref('comments', cascade="all, delete-orphan"))
