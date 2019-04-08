# -*- coding: utf-8 -*-

from sqlalchemy.ext.orderinglist import ordering_list

from . import db, BaseScopedNameMixin
from .project import Project
from .proposal import Proposal


class Labelset(BaseScopedNameMixin, db.Model):
    """
    A collection of labels, in checkbox mode (select multiple) or radio mode (select one). A project can
    contain multiple label sets.
    """
    __tablename__ = 'labelset'

    project_id = db.Column(None, db.ForeignKey('profile.id', ondelete='CASCADE'), nullable=False)
    project = db.relationship(Project)  # Backref is defined in the Project model with an ordering list
    parent = db.synonym('project')

    labels = db.relationship('Label', cascade='all, delete-orphan',
        order_by='Label.seq', collection_class=ordering_list('seq', count_from=1))

    #: Sequence number for this labelset, used in UI for ordering
    seq = db.Column(db.Integer, nullable=False)

    #: Radio mode specifies that only one of the labels in this set may be applied on a project
    radio_mode = db.Column(db.Boolean, nullable=False, default=False)
    #: Restricted model specifies that labels in this set may only be applied by someone with
    #: an editorial role (TODO: name the role)
    restricted = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)

    def __repr__(self):
        return "<Labelset %s in %s>" % (self.name, self.project.name)


proposal_label = db.Table(
    'proposal_label', db.Model.metadata,
    db.Column('proposal_id', None, db.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False, primary_key=True),
    db.Column('label_id', None, db.ForeignKey('label.id', ondelete='CASCADE'), nullable=False, primary_key=True, index=True),
    db.Column('created_at', db.DateTime, default=db.func.utcnow())
)


class Label(BaseScopedNameMixin, db.Model):
    __tablename__ = 'label'

    labelset_id = db.Column(None, db.ForeignKey('labelset.id', ondelete='CASCADE'), nullable=False)
    labelset = db.relationship(Labelset)

    #: Sequence number for this label, used in UI for ordering
    seq = db.Column(db.Integer, nullable=False)

    #: Icon for displaying in space-constrained UI. Contains emoji
    #: an emoji, or up to three ASCII characters picked from the label's title
    icon_emoji = db.Column(db.Unicode(1), nullable=True)

    #: Proposals that this label is attached to
    proposals = db.relationship(Proposal, secondary=proposal_label, lazy='dynamic', backref='labels')

    __table_args__ = (db.UniqueConstraint('labelset_id', 'name'),)

    def __repr__(self):
        return "<Label %s/%s>" % (self.labelset.name, self.name)

    @property
    def icon(self):
        result = self.icon_emoji
        if not result:
            result = ''.join(w[0] for w in self.title.strip().title().split(None, 2))
            if len(result) <= 1:
                result = self.title.strip()[:2]
        return result
