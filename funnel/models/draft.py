from __future__ import annotations

from werkzeug.datastructures import MultiDict

from . import JsonDict, NoIdMixin, UUIDType, db

__all__ = ['Draft']


class Draft(NoIdMixin, db.Model):
    """Store for autosaved, unvalidated drafts on behalf of other models."""

    __tablename__ = 'draft'

    table = db.Column(db.UnicodeText, primary_key=True)
    table_row_id = db.Column(UUIDType(binary=False), primary_key=True)
    body = db.Column(JsonDict, nullable=False, server_default='{}')
    revision = db.Column(UUIDType(binary=False))

    @property
    def formdata(self):
        return MultiDict(self.body.get('form', {}))

    @formdata.setter
    def formdata(self, value):
        if self.body is not None:
            self.body['form'] = value
        else:
            self.body = {'form': value}
