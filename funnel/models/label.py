"""Workflow label models."""

from __future__ import annotations

from typing import Union

from sqlalchemy.ext.orderinglist import ordering_list

from coaster.sqlalchemy import with_roles

from . import (
    BaseScopedNameMixin,
    Mapped,
    Model,
    TSVectorType,
    hybrid_property,
    relationship,
    sa,
)
from .helpers import add_search_trigger, reopen, visual_field_delimiter
from .project import Project
from .project_membership import project_child_role_map
from .proposal import Proposal

proposal_label = sa.Table(
    'proposal_label',
    Model.metadata,
    sa.Column(
        'proposal_id',
        sa.Integer,
        sa.ForeignKey('proposal.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    ),
    sa.Column(
        'label_id',
        sa.Integer,
        sa.ForeignKey('label.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
        index=True,
    ),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=sa.func.utcnow()),
)


class Label(BaseScopedNameMixin, Model):
    __tablename__ = 'label'
    __allow_unmapped__ = True

    project_id = sa.orm.mapped_column(
        sa.Integer, sa.ForeignKey('project.id', ondelete='CASCADE'), nullable=False
    )
    # Backref from project is defined in the Project model with an ordering list
    project: Mapped[Project] = with_roles(
        relationship(Project), grants_via={None: project_child_role_map}
    )
    # `parent` is required for
    # :meth:`~coaster.sqlalchemy.mixins.BaseScopedNameMixin.make_name()`
    parent: Mapped[Project] = sa.orm.synonym('project')

    #: Parent label's id. Do not write to this column directly, as we don't have the
    #: ability to : validate the value within the app. Always use the :attr:`main_label`
    #: relationship.
    main_label_id = sa.orm.mapped_column(
        sa.Integer,
        sa.ForeignKey('label.id', ondelete='CASCADE'),
        index=True,
        nullable=True,
    )
    # See https://docs.sqlalchemy.org/en/13/orm/self_referential.html
    options = relationship(
        'Label',
        backref=sa.orm.backref('main_label', remote_side='Label.id'),
        order_by='Label.seq',
        passive_deletes=True,
        collection_class=ordering_list('seq', count_from=1),
    )

    # TODO: Add sqlalchemy validator for `main_label` to ensure the parent's project
    # matches. Ideally add a SQL post-update trigger as well (code is in coaster's
    # add_primary_relationship)

    #: Sequence number for this label, used in UI for ordering
    seq = sa.orm.mapped_column(sa.Integer, nullable=False)

    # A single-line description of this label, shown when picking labels (optional)
    description = sa.orm.mapped_column(sa.UnicodeText, nullable=False, default='')

    #: Icon for displaying in space-constrained UI. Contains one emoji symbol.
    #: Since emoji can be composed from multiple symbols, there is no length
    #: limit imposed here
    icon_emoji = sa.orm.mapped_column(sa.UnicodeText, nullable=True)

    #: Restricted mode specifies that this label may only be applied by someone with
    #: an editorial role (TODO: name the role). If this label is a parent, it applies
    #: to all its children
    _restricted = sa.orm.mapped_column(
        'restricted', sa.Boolean, nullable=False, default=False
    )

    #: Required mode signals to UI that if this label is a parent, one of its
    #: children must be mandatorily applied to the proposal. The value of this
    #: field must be ignored if the label is not a parent
    _required = sa.orm.mapped_column(
        'required', sa.Boolean, nullable=False, default=False
    )

    #: Archived mode specifies that the label is no longer available for use
    #: although all the previous records will stay in database.
    _archived = sa.orm.mapped_column(
        'archived', sa.Boolean, nullable=False, default=False
    )

    search_vector: Mapped[TSVectorType] = sa.orm.mapped_column(
        TSVectorType(
            'name',
            'title',
            'description',
            weights={'name': 'A', 'title': 'A', 'description': 'B'},
            regconfig='english',
            hltext=lambda: sa.func.concat_ws(
                visual_field_delimiter, Label.title, Label.description
            ),
        ),
        nullable=False,
        deferred=True,
    )

    #: Proposals that this label is attached to
    proposals: Mapped[Proposal] = relationship(
        Proposal, secondary=proposal_label, back_populates='labels'
    )

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'name'),
        sa.Index('ix_label_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __roles__ = {
        'all': {
            'read': {
                'name',
                'title',
                'project',
                'seq',
                'restricted',
                'required',
                'archived',
                'main_label',
            },
        }
    }

    __datasets__ = {
        'related': {
            'name',
            'title',
            'project',
            'seq',
            'restricted',
            'required',
            'archived',
            'main_label',
            'icon_emoji',
        }
    }

    @property
    def title_for_name(self) -> str:
        if self.main_label:
            return f"{self.main_label.title}/{self.title}"
        return self.title

    @property
    def form_label_text(self) -> str:
        return (
            self.icon_emoji + " " + self.title
            if self.icon_emoji is not None
            else self.title
        )

    @property
    def has_proposals(self) -> bool:
        if not self.has_options:
            return bool(self.proposals)
        return any(bool(option.proposals) for option in self.options)

    @hybrid_property
    def restricted(self) -> bool:
        # pylint: disable=protected-access
        return self.main_label._restricted if self.main_label else self._restricted

    @restricted.inplace.setter
    def _restricted_setter(self, value: bool) -> None:
        if self.main_label:
            raise ValueError("This flag must be set on the parent")
        self._restricted = value

    @restricted.inplace.expression
    @classmethod
    def _restricted_expression(cls) -> sa.Case:
        """Return SQL Expression."""
        return sa.case(
            (
                cls.main_label_id.is_not(None),
                sa.select(Label._restricted)
                .where(Label.id == cls.main_label_id)
                .as_scalar(),
            ),
            else_=cls._restricted,
        )

    @hybrid_property
    def archived(self) -> bool:
        """Test if this label or parent label is archived."""
        return self._archived or (
            self.main_label._archived  # pylint: disable=protected-access
            if self.main_label
            else False
        )

    @archived.inplace.setter
    def _archived_setter(self, value: bool) -> None:
        """Archive this label."""
        self._archived = value

    @archived.inplace.expression
    @classmethod
    def _archived_expression(cls) -> sa.Case:
        """Return SQL Expression."""
        return sa.case(
            (cls._archived.is_(True), cls._archived),
            (
                cls.main_label_id.is_not(None),
                sa.select(Label._archived)
                .where(Label.id == cls.main_label_id)
                .as_scalar(),
            ),
            else_=cls._archived,
        )

    @hybrid_property
    def has_options(self) -> bool:
        return bool(self.options)

    @has_options.inplace.expression
    @classmethod
    def _has_options_expression(cls) -> sa.Exists:
        """Return SQL Expression."""
        return sa.exists().where(Label.main_label_id == cls.id)

    @property
    def is_main_label(self) -> bool:
        return not self.main_label

    @hybrid_property
    def required(self) -> bool:
        # pylint: disable=using-constant-test
        return self._required if self.has_options else False

    @required.inplace.setter
    def _required_setter(self, value: bool) -> None:
        if value and not self.has_options:
            raise ValueError("Labels without options cannot be mandatory")
        self._required = value

    @property
    def icon(self) -> str:
        """
        Return an icon for displaying the label in space-constrained UI.

        If an emoji icon has been specified, use it. If not, create initials
        from the title (up to 3). If the label is a single word, return the
        first three characters.
        """
        result = self.icon_emoji
        if not result:
            result = ''.join(w[0] for w in self.title.strip().title().split(None, 2))
            if len(result) <= 1:
                result = self.title.strip()[:3]
        return result

    def __repr__(self) -> str:
        """Represent :class:`Label` as a string."""
        if self.main_label:
            return f'<Label {self.main_label.name}/{self.name}>'
        return f'<Label {self.name}>'

    def apply_to(self, proposal: Proposal) -> None:
        # pylint: disable=using-constant-test
        if self.has_options:
            raise ValueError("This label requires one of its options to be used")
        if self in proposal.labels:
            return

        if self.main_label is not None:
            existing_labels = set(self.main_label.options).intersection(
                set(proposal.labels)
            )
            if existing_labels:
                # the parent label is in radio mode and one of it's labels are
                # already assigned to this proposal. We need to
                # remove the older label and assign given label.
                for elabel in existing_labels:
                    proposal.labels.remove(elabel)
        # we can assign label to proposal
        proposal.labels.append(self)

    def remove_from(self, proposal: Proposal) -> None:
        # pylint: disable=using-constant-test
        if self.has_options:
            raise ValueError("This label requires one of its options to be removed")
        if self in proposal.labels:
            proposal.labels.remove(self)


add_search_trigger(Label, 'search_vector')


class ProposalLabelProxyWrapper:
    _obj: Proposal

    def __init__(self, obj: Proposal) -> None:
        object.__setattr__(self, '_obj', obj)

    def __getattr__(self, name: str) -> Union[bool, str, None]:
        """Get an attribute."""
        # What this does:
        # 1. Check if the project has this label (including archived labels). If not,
        #    raise error
        # 2. If this is not a parent label: 2a. Check if proposal has this label set. If
        #    so, return True, else False
        # 3. If this is a parent label: 3a. If the proposal has one of the options set,
        #    return its name. If not, return None

        label = Label.query.filter(
            Label.name == name, Label.project == self._obj.project
        ).one_or_none()
        if label is None:
            raise AttributeError

        if not label.has_options:
            return label in self._obj.labels

        # Only one option from a main label should be set at a time, but we enforce
        # this in the UI, not in the db, so more than one may exist in the db.
        label_options = list(set(self._obj.labels).intersection(set(label.options)))
        return label_options[0].name if len(label_options) > 0 else None

    def __setattr__(self, name: str, value: bool) -> None:
        """Set an attribute."""
        label = Label.query.filter(
            Label.name == name,
            Label.project == self._obj.project,
            Label._archived.is_(False),
        ).one_or_none()
        if label is None:
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
                main_label=label, _archived=False, name=value
            ).one_or_none()
            if option_label is None:
                raise ValueError("Invalid option for this label")

            # Scan for conflicting labels and remove them. Iterate over a copy
            # to allow mutation of the source list during iteration
            for existing_label in list(self._obj.labels):
                if (
                    existing_label != option_label
                    and existing_label.main_label == option_label.main_label
                ):
                    self._obj.labels.remove(existing_label)

            if option_label not in self._obj.labels:
                self._obj.labels.append(option_label)


class ProposalLabelProxy:
    def __get__(
        self, obj, cls=None
    ) -> Union[ProposalLabelProxyWrapper, ProposalLabelProxy]:
        """Get proposal label proxy."""
        if obj is not None:
            return ProposalLabelProxyWrapper(obj)
        return self


@reopen(Project)
class __Project:
    labels = relationship(
        Label,
        primaryjoin=sa.and_(
            Label.project_id == Project.id,
            Label.main_label_id.is_(None),
            Label._archived.is_(False),  # pylint: disable=protected-access
        ),
        order_by=Label.seq,
        viewonly=True,
    )
    all_labels = relationship(
        Label,
        collection_class=ordering_list('seq', count_from=1),
        back_populates='project',
    )


@reopen(Proposal)
class __Proposal:
    #: For reading and setting labels from the edit form
    formlabels = ProposalLabelProxy()

    labels = with_roles(
        relationship(Label, secondary=proposal_label, back_populates='proposals'),
        read={'all'},
    )
