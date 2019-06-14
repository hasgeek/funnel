# -*- coding: utf-8 -*-

from sqlalchemy.ext.hybrid import hybrid_property
from . import db, UuidMixin, BaseScopedIdNameMixin, MarkdownColumn, UrlType, TSVectorType
from .project import Project
from .proposal import Proposal
from .venue import VenueRoom
from .helpers import add_search_trigger


__all__ = ['Session']


class Session(UuidMixin, BaseScopedIdNameMixin, db.Model):
    __tablename__ = 'session'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = db.relationship(Project,
        backref=db.backref('sessions', cascade='all, delete-orphan', lazy='dynamic'))
    parent = db.synonym('project')
    description = MarkdownColumn('description', default=u'', nullable=False)
    speaker_bio = MarkdownColumn('speaker_bio', default=u'', nullable=False)
    proposal_id = db.Column(None, db.ForeignKey('proposal.id'), nullable=True, unique=True)
    proposal = db.relationship(Proposal,
        backref=db.backref('session', uselist=False, cascade='all, delete-orphan'))
    speaker = db.Column(db.Unicode(200), default=None, nullable=True)
    start = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    end = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    venue_room_id = db.Column(None, db.ForeignKey('venue_room.id'), nullable=True)
    venue_room = db.relationship(VenueRoom, backref=db.backref('sessions'))
    is_break = db.Column(db.Boolean, default=False, nullable=False)
    featured = db.Column(db.Boolean, default=False, nullable=False)
    banner_image_url = db.Column(UrlType, nullable=True)

    search_vector = db.deferred(db.Column(
        TSVectorType(
            'title', 'description_text', 'speaker_bio_text', 'speaker',
            weights={
                'title': 'A', 'description_text': 'B', 'speaker_bio_text': 'B', 'speaker': 'A'
                },
            regconfig='english',
            ),
        nullable=False))

    __table_args__ = (
        db.UniqueConstraint('project_id', 'url_id'),
        db.CheckConstraint(
            '("start" IS NULL AND "end" IS NULL) OR ("start" IS NOT NULL AND "end" IS NOT NULL)',
            'session_start_end_check'),
        db.Index('ix_session_search_vector', 'search_vector', postgresql_using='gin'),
        )

    @hybrid_property
    def scheduled(self):
        # A session is scheduled only when both start and end fields have a value
        return self.start is not None and self.end is not None

    @scheduled.expression
    def scheduled(self):
        return (self.start != None) & (self.end != None)  # NOQA

    @classmethod
    def for_proposal(cls, proposal, create=False):
        session_obj = cls.query.filter_by(proposal=proposal).first()
        if session_obj is None and create:
            session_obj = cls(title=proposal.title, description=proposal.outline,
                speaker_bio=proposal.bio, project=proposal.project, proposal=proposal)
            db.session.add(session_obj)
        return session_obj

    def make_unscheduled(self):
        # Session is not deleted, but we remove start and end time,
        # so it becomes an unscheduled session.
        self.start = None
        self.end = None



add_search_trigger(Session, 'search_vector')
# Project schedule column expressions
# Guide: https://docs.sqlalchemy.org/en/13/orm/mapped_sql_expr.html#using-column-property
Project.schedule_start_at = db.column_property(
    db.select([db.func.min(Session.start)]
        ).where(Session.start.isnot(None)).where(Session.project_id == Project.id
        ).correlate_except(Session)
    )

Project.schedule_end_at = db.column_property(
    db.select([db.func.max(Session.end)]
        ).where(Session.end.isnot(None)).where(Session.project_id == Project.id
        ).correlate_except(Session)
    )
