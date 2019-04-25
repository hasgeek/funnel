# -*- coding: utf-8 -*-

from . import db, BaseScopedNameMixin
from .project import Project
from .commentvote import Voteset, Commentset, SET_TYPE

__all__ = ['Section']


# --- Models ------------------------------------------------------------------

class Section(BaseScopedNameMixin, db.Model):
    __tablename__ = 'section'
    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project, primaryjoin=project_id == Project.id,
        backref=db.backref('sections', cascade="all, delete-orphan"))
    parent = db.synonym('project')

    description = db.Column(db.Text, default=u'', nullable=False)
    public = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("project_id", "name"), {})

    voteset_id = db.Column(None, db.ForeignKey('voteset.id'), nullable=False)
    voteset = db.relationship(Voteset, uselist=False)

    commentset_id = db.Column(None, db.ForeignKey('commentset.id'), nullable=False)
    commentset = db.relationship(Commentset, uselist=False)

    __roles__ = {
        'all': {
            'read': {
                'id', 'name', 'title', 'description', 'public'
            },
        },
    }

    def __init__(self, **kwargs):
        super(Section, self).__init__(**kwargs)
        self.voteset = Voteset(type=SET_TYPE.PROJECT_SECTION)
        self.commentset = Commentset(type=SET_TYPE.PROJECT_SECTION)

    def permissions(self, user, inherited=None):
        perms = super(Section, self).permissions(user, inherited)
        if user is not None and user == self.project.user:
            perms.update([
                'edit-section',
                'delete-section',
            ])
        return perms
