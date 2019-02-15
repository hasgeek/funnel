# -*- coding: utf-8 -*-

from sqlalchemy_utils import UUIDType
from werkzeug.datastructures import MultiDict
from . import db, JsonDict, NoIdMixin

__all__ = ['Draft']


class Draft(NoIdMixin, db.Model):
    """Store for autosaved, unvalidated drafts on behalf of other models"""
    __tablename__ = 'draft'

    table = db.Column(db.UnicodeText, primary_key=True)
    table_row_id = db.Column(UUIDType(binary=False), primary_key=True)
    body = db.Column(JsonDict, nullable=False, server_default='{}')
    revision = db.Column(UUIDType(binary=False))

    @property
    def formdata(self):
        return MultiDict(self.body['form']) if 'form' in self.body else MultiDict({})

    @formdata.setter
    def formdata(self, value):
        self.body = {'form': value}
