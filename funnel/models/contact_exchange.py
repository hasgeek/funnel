# -*- coding: utf-8 -*-

from sqlalchemy.ext.associationproxy import association_proxy

from . import db, TimestampMixin, RoleMixin
from .user import User
from .event import Participant

__all__ = ['ContactExchange']


class ContactExchange(TimestampMixin, RoleMixin, db.Model):
    """
    Model to track who scanned whose badge, at which event.
    """
    __tablename__ = 'contact_exchange'
    #: User who scanned this contact
    user_id = db.Column(None, db.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True)
    user = db.relationship(User,
        backref=db.backref('scanned_contacts',
            lazy='dynamic',
            order_by='ContactExchange.scanned_at.desc()',
            passive_deletes=True))
    #: Participant whose contact was scanned
    participant_id = db.Column(None, db.ForeignKey('participant.id', ondelete='CASCADE'),
        primary_key=True, index=True)
    participant = db.relationship(Participant,
        backref=db.backref('scanned_contacts', passive_deletes=True))
    #: Datetime at which the scan happened
    scanned_at = db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=db.func.utcnow())
    #: Note recorded by the user (plain text)
    description = db.Column(db.UnicodeText, nullable=False, default=u'')
    #: Archived flag
    archived = db.Column(db.Boolean, nullable=False, default=False)

    __roles__ = {
        'owner': {
            'read': {'user', 'participant', 'scanned_at', 'description', 'archived'},
            'write': {'description', 'archived'},
            },
        'subject': {
            'read': {'user', 'partcipant', 'scanned_at'},
            },
        }

    def roles_for(self, actor, anchors=()):
        roles = super(ContactExchange, self).roles_for(actor, anchors)
        if actor == self.user:
            roles.add('owner')
        if actor == self.participant.user:
            roles.add('subject')
        return roles


Participant.scanning_users = association_proxy('scanned_contacts', 'user')
