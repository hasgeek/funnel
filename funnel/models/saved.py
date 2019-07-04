# -*- coding: utf-8 -*-

from . import db, NoIdMixin
from .user import User
from .project import Project
from .session import Session


class SavedProject(NoIdMixin, db.Model):
    #: User who saved this project
    user_id = db.Column(None, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, primary_key=True)
    user = db.relationship(User,
        backref=db.backref('saved_projects', lazy='dynamic', passive_deletes=True))
    #: Project that was saved
    project_id = db.Column(None, db.ForeignKey('project.id', ondelete='CASCADE'),
        nullable=False, primary_key=True, index=True)
    project = db.relationship(Project,
        backref=db.backref('saved_by', lazy='dynamic', passive_deletes=True))
    #: Timestamp when the save happened
    saved_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow())
    #: User's plaintext note to self on why they saved this (optional)
    description = db.Column(db.UnicodeText, nullable=True)

    def roles_for(self, actor, anchors=()):
        roles = super(SavedProject, self).roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('owner')
        return roles


class SavedSession(NoIdMixin, db.Model):
    #: User who saved this session
    user_id = db.Column(None, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, primary_key=True)
    user = db.relationship(User,
        backref=db.backref('saved_sessions', lazy='dynamic', passive_deletes=True))
    #: Session that was saved
    session_id = db.Column(None, db.ForeignKey('session.id', ondelete='CASCADE'),
        nullable=False, primary_key=True, index=True)
    session = db.relationship(Session,
        backref=db.backref('saved_by', lazy='dynamic', passive_deletes=True))
    #: Timestamp when the save happened
    saved_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow())
    #: User's plaintext note to self on why they saved this (optional)
    description = db.Column(db.UnicodeText, nullable=True)

    def roles_for(self, actor, anchors=()):
        roles = super(SavedSession, self).roles_for(actor, anchors)
        if actor is not None and actor == self.user:
            roles.add('owner')
        return roles


User.saved_sessions_in = lambda self, project: self.saved_sessions.join(Session
    ).filter(Session.project == project)
