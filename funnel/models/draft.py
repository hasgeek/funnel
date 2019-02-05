# -*- coding: utf-8 -*-

from sqlalchemy_utils import UUIDType
from . import db, JsonDict, IdMixin

__all__ = ['Draft']


class Draft(IdMixin, db.Model):
    """Generic model to store unvalidated draft of any other models"""
    __tablename__ = 'draft'
    __uuid_primary_key__ = True

    table = db.Column(db.UnicodeText)
    table_row_id = db.Column(UUIDType(binary=False))
    body = db.Column(JsonDict, nullable=False, server_default='{}')
    revision = db.Column(UUIDType(binary=False))
