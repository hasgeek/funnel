"""Model for unvalidated drafts for web forms."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from werkzeug.datastructures import MultiDict

from . import Mapped, NoIdMixin, UUIDType, db, json_type, sa

__all__ = ['Draft']


class Draft(NoIdMixin, db.Model):  # type: ignore[name-defined]
    """Store for autosaved, unvalidated drafts on behalf of other models."""

    __tablename__ = 'draft'
    __allow_unmapped__ = True

    table = sa.Column(sa.UnicodeText, primary_key=True)
    table_row_id: Mapped[UUID] = sa.Column(UUIDType(binary=False), primary_key=True)
    body = sa.Column(json_type, nullable=False, server_default='{}')
    revision: Mapped[Optional[UUID]] = sa.Column(UUIDType(binary=False))

    @property
    def formdata(self):
        return MultiDict(self.body.get('form', {}))

    @formdata.setter
    def formdata(self, value):
        if self.body is not None:
            self.body['form'] = value
        else:
            self.body = {'form': value}
