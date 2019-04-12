# -*- coding: utf-8 -*-

from sqlalchemy import func
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.hybrid import hybrid_property

from coaster.sqlalchemy import with_roles

from . import db, BaseScopedNameMixin
from .project import Project
from .proposal import Proposal


class Labelset(BaseScopedNameMixin, db.Model):
    """
    A collection of labels, in checkbox mode (select multiple) or radio mode (select one). A project can
    contain multiple labelsets.
    """
    __tablename__ = 'labelset'

    project_id = db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    project = db.relationship(Project)  # Backref is defined in the Project model with an ordering list
    parent = db.synonym('project')

    labels = db.relationship('Label', cascade='all, delete-orphan',
        order_by='Label.seq', collection_class=ordering_list('seq', count_from=1))

    #: Sequence number for this labelset, used in UI for ordering
    seq = db.Column(db.Integer, nullable=False)

    # A single-line description of this labelset, shown when applying labels
    description = db.Column(db.UnicodeText, nullable=False)

    #: Radio mode specifies that only one of the labels in this set may be applied on a project
    radio_mode = db.Column(db.Boolean, nullable=False, default=False)

    #: Restricted mode specifies that labels in this set may only be applied by someone with
    #: an editorial role (TODO: name the role)
    restricted = db.Column(db.Boolean, nullable=False, default=False)

    #: Required mode specifies that a label from this set must be applied on a proposal.
    #: This is not foolproof and can be violated under a variety of conditions including
    #: (a) this flag being set after a proposal is created, and (b) a proposal being moved
    #: across projects
    required = db.Column(db.Boolean, nullable=False, default=False)

    #: Archived mode specifies that the labelset is no longer available for use
    #: although all the previous records will stay in database.
    archived = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)

    def __repr__(self):
        return "<Labelset %s in %s>" % (self.name, self.project.name)

    __roles__ = {
        'all': {
            'read': {
                'name', 'title', 'project_id', 'seq', 'description', 'radio_code',
                'restricted', 'required'
            }
        }
    }

    @hybrid_property
    def form_name(self):
        """
        Generates a name to be used in forms when a field is created for this labelset
        """
        return 'labelset_' + self.name.replace('-', '_')

    @form_name.expression
    def form_name(cls):
        return func.concat('labelset_', func.replace(cls.name, '-', '_'))

    def roles_for(self, actor=None, anchors=()):
        roles = super(Labelset, self).roles_for(actor, anchors)
        roles.update(self.project.roles_for(actor, anchors))
        return roles

    @with_roles(call={'admin'})
    def assign_label(self, label):
        """
        This function takes a Label object and links the labelset with it.
        This function requires role control. Hence this function must be called
        via ``current_access()``.

        :param label: A Label instance
        """
        self.labels.append(label)


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
    parent = db.synonym('labelset')

    #: Color code to be used in UI with this label
    bgcolor = db.Column(db.Unicode(6), nullable=False, default=u"CCCCCC")

    #: Sequence number for this label, used in UI for ordering
    seq = db.Column(db.Integer, nullable=False)

    #: Icon for displaying in space-constrained UI. Contains emoji
    icon_emoji = db.Column(db.Unicode(1), nullable=True)

    #: Archived mode specifies that the label is no longer available for use
    #: although all the previous records will stay in database.
    archived = db.Column(db.Boolean, nullable=False, default=False)

    #: Proposals that this label is attached to
    proposals = db.relationship(Proposal, secondary=proposal_label, lazy='dynamic', backref='labels')

    __table_args__ = (db.UniqueConstraint('labelset_id', 'name'),)

    def __repr__(self):
        return "<Label %s/%s>" % (self.labelset.name, self.name)

    @property
    def icon(self):
        """
        Returns an icon for displaying the label in space-constrained UI.
        If an emoji icon has been specified, use it. If not, create initials
        from the title (up to 3). If the label is a single word, returns the
        first three characters.
        """
        result = self.icon_emoji
        if not result:
            result = ''.join(w[0] for w in self.title.strip().title().split(None, 2))
            if len(result) <= 1:
                result = self.title.strip()[:3]
        return result
