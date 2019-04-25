# -*- coding: utf-8 -*-

from . import db, make_timestamp_columns, TimestampMixin, BaseScopedNameMixin
from .profile import Profile
from .project import Project
from .proposal import Proposal


class Labelset(BaseScopedNameMixin, db.Model):
    """
    A collection of labels, in checkbox mode (select multiple) or radio mode (select one). A profile can
    contain multiple label sets and a Project can enable one or more sets to be used in Proposals.
    """
    __tablename__ = 'labelset'

    profile_id = db.Column(None, db.ForeignKey('profile.id'), nullable=False)
    profile = db.relationship(Profile, backref=db.backref('labelsets', cascade='all, delete-orphan'))
    parent = db.synonym('profile')

    radio_mode = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (db.UniqueConstraint('profile_id', 'name'),)

    def __repr__(self):
        return "<Labelset %s in %s>" % (self.name, self.profile.name)


proposal_label = db.Table(
    'proposal_label', db.Model.metadata,
    *(make_timestamp_columns() + (
        db.Column('proposal_id', None, db.ForeignKey('proposal.id'), nullable=False, primary_key=True),
        db.Column('label_id', None, db.ForeignKey('label.id'), nullable=False, primary_key=True)
    )))


class Label(BaseScopedNameMixin, db.Model):
    __tablename__ = 'label'

    labelset_id = db.Column(None, db.ForeignKey('labelset.id'), nullable=False)
    labelset = db.relationship(Labelset)

    proposals = db.relationship(Proposal, secondary=proposal_label, backref='labels')

    __table_args__ = (db.UniqueConstraint('labelset_id', 'name'),)

    def __repr__(self):
        return "<Label %s/%s>" % (self.labelset.name, self.name)


class ProjectLabelset(TimestampMixin, db.Model):
    __tablename__ = 'project_labelset'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False, primary_key=True)
    project = db.relationship(Project, backref=db.backref('labelset_links', cascade='all, delete-orphan'))
    labelset_id = db.Column(None, db.ForeignKey('labelset.id'), nullable=False, primary_key=True)
    labelset = db.relationship(Labelset, backref=db.backref('project_links', cascade='all, delete-orphan'))
    seq = db.Column(db.Integer, nullable=False, default=0)


# TODO: Should this be just a secondary table?
# class ProposalLabel(TimestampMixin, db.Model):
#     __tablename__ = 'proposal_label'

#     proposal_id = db.Column(None, db.ForeignKey('proposal.id'), nullable=False, primary_key=True)
#     proposal = db.relationship(Proposal, backref=db.backref('label_links', cascade='all, delete-orphan'))
#     label_id = db.Column(None, db.ForeignKey('label.id'), nullable=False, primary_key=True)
#     label = db.relationship(Label, backref=db.backref('proposal_links', cascade='all, delete-orphan'))
