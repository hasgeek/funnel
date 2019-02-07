# -*- coding: utf-8 -*-

from sqlalchemy_utils import UUIDType
from . import db, JsonDict, NoIdMixin, TimestampMixin

__all__ = ['Draft']


class Draft(NoIdMixin, TimestampMixin, db.Model):
    """Store for autosaved, unvalidated drafts on behalf of other models"""
    __tablename__ = 'draft'
    __uuid_primary_key__ = True

    table = db.Column(db.UnicodeText, primary_key=True)
    table_row_id = db.Column(UUIDType(binary=False), primary_key=True)
    body = db.Column(JsonDict, nullable=False, server_default='{}')
    revision = db.Column(UUIDType(binary=False))
