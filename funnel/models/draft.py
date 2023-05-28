"""Model for unvalidated drafts for web forms."""

from __future__ import annotations

from typing import Optional, Union
from uuid import UUID

from werkzeug.datastructures import MultiDict

from . import Mapped, Model, NoIdMixin, sa, types

__all__ = ['Draft']


class Draft(NoIdMixin, Model):
    """Store for autosaved, unvalidated drafts on behalf of other models."""

    __tablename__ = 'draft'

    table: Mapped[types.text] = sa.orm.mapped_column(primary_key=True)
    table_row_id: Mapped[UUID] = sa.orm.mapped_column(primary_key=True)
    body: Mapped[Optional[types.jsonb_dict]]  # Optional only when instance is new
    revision: Mapped[Optional[UUID]]

    @property
    def formdata(self) -> MultiDict:
        return MultiDict(self.body.get('form', {}) if self.body is not None else {})

    @formdata.setter
    def formdata(self, value: Union[MultiDict, dict]) -> None:
        if self.body is not None:
            self.body['form'] = value
        else:
            self.body = {'form': value}
