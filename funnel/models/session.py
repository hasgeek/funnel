from sqlalchemy.ext.hybrid import hybrid_property

from werkzeug.utils import cached_property

from baseframe import localize_timezone
from coaster.sqlalchemy import with_roles

from . import (
    BaseScopedIdNameMixin,
    MarkdownColumn,
    TSVectorType,
    UrlType,
    UuidMixin,
    db,
)
from .helpers import add_search_trigger, reopen, visual_field_delimiter
from .project import Project
from .project_membership import project_child_role_map
from .proposal import Proposal
from .venue import VenueRoom
from .video import VideoMixin

__all__ = ['Session']


class Session(UuidMixin, BaseScopedIdNameMixin, VideoMixin, db.Model):
    __tablename__ = 'session'

    project_id = db.Column(None, db.ForeignKey('project.id'), nullable=False)
    project = with_roles(
        db.relationship(
            Project, backref=db.backref('sessions', cascade='all', lazy='dynamic')
        ),
        grants_via={None: project_child_role_map},
    )
    parent = db.synonym('project')
    description = MarkdownColumn('description', default='', nullable=False)
    speaker_bio = MarkdownColumn('speaker_bio', default='', nullable=False)
    proposal_id = db.Column(
        None, db.ForeignKey('proposal.id'), nullable=True, unique=True
    )
    proposal = db.relationship(
        Proposal, backref=db.backref('session', uselist=False, cascade='all')
    )
    speaker = db.Column(db.Unicode(200), default=None, nullable=True)
    start_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    end_at = db.Column(db.TIMESTAMP(timezone=True), nullable=True, index=True)
    venue_room_id = db.Column(None, db.ForeignKey('venue_room.id'), nullable=True)
    venue_room = db.relationship(VenueRoom, backref=db.backref('sessions'))
    is_break = db.Column(db.Boolean, default=False, nullable=False)
    featured = db.Column(db.Boolean, default=False, nullable=False)
    banner_image_url = db.Column(UrlType, nullable=True)

    search_vector = db.deferred(
        db.Column(
            TSVectorType(
                'title',
                'description_text',
                'speaker_bio_text',
                'speaker',
                weights={
                    'title': 'A',
                    'description_text': 'B',
                    'speaker_bio_text': 'B',
                    'speaker': 'A',
                },
                regconfig='english',
                hltext=lambda: db.func.concat_ws(
                    visual_field_delimiter,
                    Session.title,
                    Session.speaker,
                    Session.description_html,
                    Session.speaker_bio_html,
                ),
            ),
            nullable=False,
        )
    )

    __table_args__ = (
        db.UniqueConstraint('project_id', 'url_id'),
        db.CheckConstraint(
            '("start_at" IS NULL AND "end_at" IS NULL) OR ("start_at" IS NOT NULL AND "end_at" IS NOT NULL)',
            'session_start_at_end_at_check',
        ),
        db.Index('ix_session_search_vector', 'search_vector', postgresql_using='gin'),
    )

    __roles__ = {
        'all': {
            'read': {
                'created_at',
                'updated_at',
                'title',
                'project',
                'speaker',
                'user',
                'featured',
                'description',
                'speaker_bio',
                'start_at',
                'end_at',
                'venue_room',
                'is_break',
                'banner_image_url',
                'start_at_localized',
                'end_at_localized',
                'scheduled',
                'video',
                'proposal',
            },
            'call': {'url_for'},
        }
    }

    __datasets__ = {
        'primary': {
            'uuid_b58',
            'title',
            'speaker',
            'user',
            'featured',
            'description',
            'speaker_bio',
            'start_at',
            'end_at',
            'venue_room',
            'is_break',
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
        'without_parent': {
            'uuid_b58',
            'title',
            'speaker',
            'user',
            'featured',
            'description',
            'speaker_bio',
            'start_at',
            'end_at',
            'venue_room',
            'is_break',
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
        'related': {
            'uuid_b58',
            'title',
            'speaker',
            'user',
            'featured',
            'description',
            'speaker_bio',
            'start_at',
            'end_at',
            'venue_room',
            'is_break',
            'banner_image_url',
            'start_at_localized',
            'end_at_localized',
        },
    }

    @hybrid_property
    def user(self):
        if self.proposal:
            return self.proposal.speaker

    @hybrid_property
    def scheduled(self):
        # A session is scheduled only when both start and end fields have a value
        return self.start_at is not None and self.end_at is not None

    @scheduled.expression
    def scheduled(self):
        return (self.start_at.isnot(None)) & (self.end_at.isnot(None))

    @cached_property
    def start_at_localized(self):
        return (
            localize_timezone(self.start_at, tz=self.project.timezone)
            if self.start_at
            else None
        )

    @cached_property
    def end_at_localized(self):
        return (
            localize_timezone(self.end_at, tz=self.project.timezone)
            if self.end_at
            else None
        )

    @classmethod
    def for_proposal(cls, proposal, create=False):
        session_obj = cls.query.filter_by(proposal=proposal).first()
        if session_obj is None and create:
            session_obj = cls(
                title=proposal.title,
                description=proposal.outline,
                speaker_bio=proposal.bio,
                project=proposal.project,
                proposal=proposal,
            )
            db.session.add(session_obj)
        return session_obj

    def make_unscheduled(self):
        # Session is not deleted, but we remove start and end time,
        # so it becomes an unscheduled session.
        self.start_at = None
        self.end_at = None


add_search_trigger(Session, 'search_vector')


@reopen(Project)
class Project:
    # Project schedule column expressions
    # Guide: https://docs.sqlalchemy.org/en/13/orm/mapped_sql_expr.html#using-column-property
    schedule_start_at = with_roles(
        db.column_property(
            db.select([db.func.min(Session.start_at)])
            .where(Session.start_at.isnot(None))
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
        ),
        read={'all'},
    )

    next_session_at = with_roles(
        db.column_property(
            db.select([db.func.min(Session.start_at)])
            .where(Session.start_at.isnot(None))
            .where(Session.start_at > db.func.utcnow())
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
        ),
        read={'all'},
    )

    schedule_end_at = with_roles(
        db.column_property(
            db.select([db.func.max(Session.end_at)])
            .where(Session.end_at.isnot(None))
            .where(Session.project_id == Project.id)
            .correlate_except(Session)
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def session_count(self):
        return self.sessions.filter(Session.start_at.isnot(None)).count()

    featured_sessions = with_roles(
        db.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=db.and_(
                Session.project_id == Project.id, Session.featured.is_(True)
            ),
        ),
        read={'all'},
    )
    scheduled_sessions = with_roles(
        db.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=db.and_(Session.project_id == Project.id, Session.scheduled),
        ),
        read={'all'},
    )
    unscheduled_sessions = with_roles(
        db.relationship(
            Session,
            order_by=Session.start_at.asc(),
            primaryjoin=db.and_(
                Session.project_id == Project.id, Session.scheduled.isnot(True)
            ),
        ),
        read={'all'},
    )

    sessions_with_video = with_roles(
        db.relationship(
            Session,
            lazy='dynamic',
            primaryjoin=db.and_(
                Project.id == Session.project_id,
                Session.video_id.isnot(None),
                Session.video_source.isnot(None),
            ),
        ),
        read={'all'},
    )

    @with_roles(read={'all'})
    @cached_property
    def has_sessions_with_video(self):
        return self.query.session.query(self.sessions_with_video.exists()).scalar()

    def next_session_from(self, timestamp):
        """
        Find the next session in this project starting at or after given timestamp.
        """
        return (
            self.sessions.filter(
                Session.start_at.isnot(None), Session.start_at >= timestamp
            )
            .order_by(Session.start_at.asc())
            .first()
        )

    @classmethod
    def starting_at(cls, timestamp, within, gap):
        """
        Returns projects that are about to start, for sending notifications.

        :param datetime timestamp: The timestamp to look for new sessions at
        :param timedelta within: Find anything at timestamp + within delta. Lookup will
            be for sessions where timestamp >= start_at < timestamp+within
        :param timedelta gap: A project will be considered to be starting if it has no
            sessions ending within the gap period before the timestamp

        Typical use of this method is from a background worker that calls it at
        intervals of five minutes with parameters (timestamp, within 5m, 60m gap).
        """
        # As a rule, start_at is queried with >= and <, end_at with > and <= because
        # they represent inclusive lower and upper bounds.
        return (
            cls.query.filter(
                cls.id.in_(
                    db.session.query(db.func.distinct(Session.project_id)).filter(
                        Session.start_at.isnot(None),
                        Session.start_at >= timestamp,
                        Session.start_at < timestamp + within,
                        Session.project_id.notin_(
                            db.session.query(
                                db.func.distinct(Session.project_id)
                            ).filter(
                                Session.start_at.isnot(None),
                                db.or_(
                                    db.and_(
                                        Session.start_at >= timestamp - gap,
                                        Session.start_at < timestamp,
                                    ),
                                    db.and_(
                                        Session.end_at > timestamp - gap,
                                        Session.end_at <= timestamp,
                                    ),
                                ),
                            )
                        ),
                    )
                )
            )
            .join(Session.project)
            .filter(Project.state.PUBLISHED, Project.schedule_state.PUBLISHED)
        )
