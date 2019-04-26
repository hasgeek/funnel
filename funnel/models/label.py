# -*- coding: utf-8 -*-

from sqlalchemy.sql import case, exists
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
    #: validate the value within the app. Always use the :attr:`main_label` relationship.
    main_label_id = db.Column(
        'main_label_id',
        None,
        db.ForeignKey('label.id', ondelete='CASCADE'),
        index=True,
        nullable=True
    )
    # See https://docs.sqlalchemy.org/en/13/orm/self_referential.html
    options = db.relationship(
        'Label',
        backref=db.backref('main_label', remote_side='Label.id'),
        order_by='Label.seq',
        collection_class=ordering_list('seq', count_from=1)
    )

    # TODO: Add sqlalchemy validator for `main_label` to ensure the parent's project matches.
    # Ideally add a SQL post-update trigger as well (code is in coaster's add_primary_relationship)

    #: Sequence number for this label, used in UI for ordering
    seq = db.Column(db.Integer, nullable=False)

    # A single-line description of this label, shown when picking labels (optional)
    description = db.Column(db.UnicodeText, nullable=False, default=u"")

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
    proposals = db.relationship(Proposal, secondary=proposal_label, backref='labels')

    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)

    __roles__ = {
        'all': {
            'read': {
                'name', 'title', 'project_id', 'project', 'seq',
                'restricted', 'required', 'archived'
            }
        }
    }

    @property
    def form_label_text(self):
        return self.icon_emoji + " " + self.title if self.icon_emoji is not None else self.title

    @property
    def has_proposals(self):
        if not self.has_options:
            return bool(self.proposals)
        else:
            return any(bool(option.proposals) for option in self.options)

    @hybrid_property
    def restricted(self):
        return self.main_label._restricted if self.main_label else self._restricted

    @restricted.setter
    def restricted(self, value):
        if self.main_label:
            raise ValueError("This flag must be set on the parent")
        self._restricted = value

    @restricted.expression
    def restricted(cls):
        return case([
            (cls.main_label_id != None, db.select([Label._restricted]).where(Label.id == cls.main_label_id).as_scalar())  # NOQA
        ], else_=cls._restricted)

    @hybrid_property
    def archived(self):
        return self._archived or (self.main_label._archived if self.main_label else False)

    @archived.setter
    def archived(self, value):
        self._archived = value

    @archived.expression
    def archived(cls):
        return case([
            (cls._archived == True, cls._archived),  # NOQA
            (cls.main_label_id != None, db.select([Label._archived]).where(Label.id == cls.main_label_id).as_scalar())  # NOQA
        ], else_=cls._archived)

    @hybrid_property
    def has_options(self):
        return bool(self.options)

    @has_options.expression
    def has_options(cls):
        return exists().where(Label.main_label_id == cls.id)

    @property
    def is_main_label(self):
        return not self.main_label

    @hybrid_property
    def required(self):
        return self._required if self.has_options else False

    @required.setter
    def required(self, value):
        if value and not self.has_options:
            raise ValueError("Labels without options cannot be mandatory")
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
        if self.main_label:
            return "<Label %s/%s>" % (self.main_label.name, self.name)
        else:
            return "<Label %s>" % self.name

    def roles_for(self, actor=None, anchors=()):
        roles = super(Label, self).roles_for(actor, anchors)
        roles.update(self.project.roles_for(actor, anchors))
        return roles

    def apply_to(self, proposal):
        if self.has_options:
            raise ValueError("This label requires one of its options to be used")
        if self in proposal.labels:
            return

        if self.main_label is not None:
            existing_labels = set(self.main_label.options).intersection(set(proposal.labels))
            if existing_labels:
                # the parent label is in radio mode and one of it's labels are
                # already assigned to this proposal. We need to
                # remove the older label and assign given label.
                for elabel in existing_labels:
                    proposal.labels.remove(elabel)
        # we can assign label to proposal
        proposal.labels.append(self)

    def remove_from(self, proposal):
        if self.has_options:
            raise ValueError("This label requires one of its options to be removed")
        if self in proposal.labels:
            proposal.labels.remove(self)


class ProposalLabelProxyWrapper(object):
    def __init__(self, obj):
        object.__setattr__(self, '_obj', obj)

    def __getattr__(self, name):
        # What this does:
        # 1. Check if the project has this label (including archived labels). If not, raise error
        # 2. If this is not a parent label:
        # 2a. Check if proposal has this label set. If so, return True, else False
        # 3. If this is a parent label:
        # 3a. If the proposal has one of the options set, return its name. If not, return None

        label = Label.query.filter(
            Label.name == name, Label.project == self._obj.project
        ).one_or_none()
        if not label:
            raise AttributeError

        if not label.has_options:
            return label in self._obj.labels

        # Only one option from a main label should be set at a time, but we enforce
        # this in the UI, not in the db, so more than one may exist in the db.
        label_options = list(set(self._obj.labels).intersection(set(label.options)))
        return label_options[0].name if len(label_options) > 0 else None

    def __setattr__(self, name, value):
        label = Label.query.filter(
            Label.name == name, Label.project == self._obj.project, Label._archived == False
        ).one_or_none()  # NOQA
        if not label:
            raise AttributeError

        if not label.has_options:
            if value is True:
                if label not in self._obj.labels:
                    self._obj.labels.append(label)
            elif value is False:
                if label in self._obj.labels:
                    self._obj.labels.remove(label)
            else:
                raise ValueError("This label can only be set to True or False")
        else:
            option_label = Label.query.filter_by(
                main_label=label,
                _archived=False,
                name=value).one_or_none()
            if not option_label:
                raise ValueError("Invalid option for this label")

            # Scan for conflicting labels and remove them. Iterate over a copy
            # to allow mutation of the source list during iteration
            for existing_label in list(self._obj.labels):
                if existing_label != option_label and existing_label.main_label == option_label.main_label:
                    self._obj.labels.remove(existing_label)

            if option_label not in self._obj.labels:
                self._obj.labels.append(option_label)


class ProposalLabelProxy(object):
    def __get__(self, obj, cls=None):
        if obj is not None:
            return ProposalLabelProxyWrapper(obj)
        else:
            return self


#: For reading and setting labels from the edit form
Proposal.formlabels = ProposalLabelProxy()
