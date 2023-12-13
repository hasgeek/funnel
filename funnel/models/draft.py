"""Model for unvalidated drafts for web forms."""

from __future__ import annotations

from uuid import UUID

from werkzeug.datastructures import MultiDict

from . import Mapped, Model, NoIdMixin, sa_orm, types

__all__ = ['Draft']


class Draft(NoIdMixin, Model):
    """Store for autosaved, unvalidated drafts on behalf of other models."""

    __tablename__ = 'draft'

    table: Mapped[types.text] = sa_orm.mapped_column(primary_key=True)
    table_row_id: Mapped[UUID] = sa_orm.mapped_column(primary_key=True)
    body: Mapped[types.jsonb_dict | None]  # Optional only when instance is new
    revision: Mapped[UUID | None]

    @property
    def formdata(self) -> MultiDict:
        return MultiDict(self.body.get('form', {}) if self.body is not None else {})

    @formdata.setter
    def formdata(self, value: MultiDict | dict) -> None:
        if self.body is not None:
            self.body['form'] = value
        else:
            self.body = {'form': value}
