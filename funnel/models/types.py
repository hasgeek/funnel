"""Python to SQLAlchemy type mappings."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import mapped_column
from sqlalchemy_json import mutable_json_type
from typing_extensions import Annotated, TypeAlias
import sqlalchemy as sa

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
    'unicode',
    'text',
    'jsonb',
    'jsonb_dict',
    'char2',
    'char3',
    'str3',
    'str16',
]

unicode: TypeAlias = Annotated[str, mapped_column(sa.Unicode())]
text: TypeAlias = Annotated[str, mapped_column(sa.UnicodeText())]
jsonb: TypeAlias = Annotated[
    dict,
    sa.orm.mapped_column(
        # FIXME: mutable_json_type assumes `dict|list`, not just `dict`
        mutable_json_type(
            dbtype=sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nested=True
        )
    ),
]
jsonb_dict: TypeAlias = Annotated[
    dict,
    sa.orm.mapped_column(
        # FIXME: mutable_json_type assumes `dict|list`, not just `dict`
        mutable_json_type(
            dbtype=sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nested=True
        ),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    ),
]

# Specialised types
char2: TypeAlias = Annotated[str, mapped_column(sa.CHAR(2))]
char3: TypeAlias = Annotated[str, mapped_column(sa.CHAR(3))]
str3: TypeAlias = Annotated[str, mapped_column(sa.Unicode(3))]
str16: TypeAlias = Annotated[str, mapped_column(sa.Unicode(16))]
