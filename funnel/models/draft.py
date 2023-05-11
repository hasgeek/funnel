"""Model for unvalidated drafts for web forms."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from werkzeug.datastructures import MultiDict

from . import Mapped, NoIdMixin, db, json_type, postgresql, sa

__all__ = ['Draft']


class Draft(NoIdMixin, db.Model):  # type: ignore[name-defined]
    """Store for autosaved, unvalidated drafts on behalf of other models."""

    __tablename__ = 'draft'
    __allow_unmapped__ = True

    table = sa.Column(sa.UnicodeText, primary_key=True)
    table_row_id: Mapped[UUID] = sa.Column(postgresql.UUID, primary_key=True)
    body = sa.Column(json_type, nullable=False, server_default='{}')
    revision: Mapped[Optional[UUID]] = sa.Column(postgresql.UUID)

    @property
    def formdata(self):
        return MultiDict(self.body.get('form', {}))

    @formdata.setter
    def formdata(self, value):
        if self.body is not None:
            self.body['form'] = value
        else:
            self.body = {'form': value}
