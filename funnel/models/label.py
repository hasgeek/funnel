# -*- coding: utf-8 -*-

from sqlalchemy.sql import exists
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.hybrid import hybrid_property

from . import db, BaseScopedNameMixin
from .project import Project
from .proposal import Proposal


proposal_label = db.Table(
    'proposal_label', db.Model.metadata,
    db.Column('proposal_id', None, db.ForeignKey('proposal.id', ondelete='CASCADE'), nullable=False, primary_key=True),
    db.Column('label_id', None, db.ForeignKey('label.id', ondelete='CASCADE'), nullable=False, primary_key=True, index=True),
    db.Column('created_at', db.DateTime, default=db.func.utcnow())
)


class Label(BaseScopedNameMixin, db.Model):
    __tablename__ = 'label'

    project_id = db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False)
    project = db.relationship(Project)  # Backref is defined in the Project model with an ordering list
    # `parent` is required for :meth:`~coaster.sqlalchemy.mixins.BaseScopedNameMixin.make_name()`
    parent = db.synonym('project')

    #: Parent label's id. Do not write to this column directly, as we don't have the ability to
    #: validate the value within the app. Always use the :attr:`parent_label` relationship.
    _parent_label_id = db.Column(
        'parent_label_id',
        None,
        db.ForeignKey('label.id', ondelete='CASCADE'),
        index=True,
        nullable=True
    )
    # See https://docs.sqlalchemy.org/en/13/orm/self_referential.html
    children = db.relationship(
        'Label',
        backref=db.backref('parent_label', remote_side='Label.id'),
        order_by='Label.seq',
        collection_class=ordering_list('seq', count_from=1)
    )

    # TODO: Add sqlalchemy validator for `parent_label` to ensure the parent's project matches.
    # Ideally add a SQL post-update trigger as well (code is in coaster's add_primary_relationship)

    #: Sequence number for this label, used in UI for ordering
    seq = db.Column(db.Integer, nullable=False)

    # A single-line description of this label, shown when picking labels (optional)
    description = db.Column(db.UnicodeText, nullable=False)

    #: Icon for displaying in space-constrained UI. Contains one emoji symbol.
    #: Since emoji can be composed from multiple symbols, there is no length
    #: limit imposed here
    icon_emoji = db.Column(db.UnicodeText, nullable=True)

    #: Restricted mode specifies that this label may only be applied by someone with
    #: an editorial role (TODO: name the role). If this label is a parent, it applies
    #: to all its children
    _restricted = db.Column('restricted', db.Boolean, nullable=False, default=False)

    #: Required mode signals to UI that if this label is a parent, one of its
    #: children must be mandatorily applied to the proposal. The value of this
    #: field must be ignored if the label is not a parent
    _required = db.Column('required', db.Boolean, nullable=False, default=False)

    #: Archived mode specifies that the label is no longer available for use
    #: although all the previous records will stay in database.
    _archived = db.Column('archived', db.Boolean, nullable=False, default=False)

    #: Proposals that this label is attached to
    proposals = db.relationship(Proposal, secondary=proposal_label, lazy='dynamic', backref='labels')

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'name', 'title', 'project_id', 'project', 'seq',
                'restricted', 'required', 'archived'
            }
        }
    }

    @hybrid_property
    def restricted(self):
        return self.parent_label._restricted if self.parent_label else self._restricted

    @hybrid_property
    def archived(self):
        return self._archived or self.parent_label._archived if self.parent_label else False

    # TODO: setter and expression for :meth:`restricted`, :meth:`archived`

    @hybrid_property
    def is_parent(self):
        return len(self.children) != 0

    # TODO: Check whether this expression works
    @is_parent.expression
    def is_parent(cls):
        return exists().where(Label._parent_label_id == cls.id)

    @hybrid_property
    def required(self):
        return self._required if self.is_parent else False

    @required.setter
    def required(self, value):
        if value and not self.is_parent:
            raise ValueError("Label without children cannot be required")
        self._required = value

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

    def __repr__(self):
        return "<Label %s/%s>" % (self.labelset.name, self.name)

    def roles_for(self, actor=None, anchors=()):
        roles = super(Label, self).roles_for(actor, anchors)
        roles.update(self.project.roles_for(actor, anchors))
        return roles
