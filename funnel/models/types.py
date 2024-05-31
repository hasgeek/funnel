"""Python to SQLAlchemy type mappings."""

from typing import Annotated, TypeAlias

import sqlalchemy as sa
import sqlalchemy.orm as sa_orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import mapped_column
from sqlalchemy_json import mutable_json_type

from coaster.sqlalchemy import (
    bigint,
    int_pkey,
    smallint,
    timestamp,
    timestamp_now,
    uuid4_pkey,
)

__all__ = [
    'int_pkey',
    'uuid4_pkey',
    'bigint',
    'smallint',
    'timestamp',
    'timestamp_now',
    'Unicode',
    'Text',
    'Jsonb',
    'JsonbDict',
    'Char2',
    'Char3',
    'Str3',
    'Str16',
]

Unicode: TypeAlias = Annotated[str, mapped_column(sa.Unicode())]
Text: TypeAlias = Annotated[str, mapped_column(sa.UnicodeText())]
Jsonb: TypeAlias = Annotated[
    dict,
    sa_orm.mapped_column(
        # FIXME: mutable_json_type assumes `dict|list`, not just `dict`
        mutable_json_type(
            dbtype=sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nested=True
        )
    ),
]
JsonbDict: TypeAlias = Annotated[
    dict,
    sa_orm.mapped_column(
        # FIXME: mutable_json_type assumes `dict|list`, not just `dict`
        mutable_json_type(
            dbtype=sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nested=True
        ),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    ),
]

# Specialised types
Char2: TypeAlias = Annotated[str, mapped_column(sa.CHAR(2))]
Char3: TypeAlias = Annotated[str, mapped_column(sa.CHAR(3))]
Str3: TypeAlias = Annotated[str, mapped_column(sa.Unicode(3))]
Str16: TypeAlias = Annotated[str, mapped_column(sa.Unicode(16))]
