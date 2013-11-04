# -*- coding: utf-8 -*-

from flask import url_for
from . import db, BaseScopedNameMixin
from .user import User
from .space import ProposalSpace

__all__ = ['UserGroup']


# --- Models ------------------------------------------------------------------

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
