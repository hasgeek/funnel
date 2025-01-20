"""Model base class and shared imports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
import sqlalchemy.orm as sa_orm
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, declarative_mixin, declared_attr
from sqlalchemy_utils import LocaleType, TimezoneType, TSVectorType

from coaster.sqlalchemy import (
    AppenderQuery,
    BaseIdNameMixin,
    BaseMixin,
    BaseNameMixin,
    BaseScopedIdMixin,
    BaseScopedIdNameMixin,
    BaseScopedNameMixin,
    CoordinatesMixin,
    DynamicMapped,
    ModelBase,
    NoIdMixin,
    Query,
    QueryProperty,
    RegistryMixin,
    RoleMixin,
    TimestampMixin,
    UrlType,
    UuidMixin,
    backref,
    relationship,
    with_roles,
)

if TYPE_CHECKING:
    from _typeshed.dbapi import DBAPIConnection


class Model(AsyncAttrs, ModelBase, DeclarativeBase):
    """Base for all models."""

    __table__: ClassVar[Table]
    __with_timezone__ = True


class GeonameModel(AsyncAttrs, ModelBase, DeclarativeBase):
    """Base for geoname models."""

    __table__: ClassVar[Table]
    __bind_key__ = 'geoname'
    __with_timezone__ = True


# This must be set _before_ any of the models using db.Model are imported
TimestampMixin.__with_timezone__ = True

db: SQLAlchemy = SQLAlchemy(
    query_class=Query,  # type: ignore[arg-type]
    metadata=Model.metadata,
)
Model.init_flask_sqlalchemy(db)
GeonameModel.init_flask_sqlalchemy(db)


@event.listens_for(Engine, 'connect')
def _emit_engine_directives(
    dbapi_connection: DBAPIConnection, _connection_record: Any
) -> None:
    """Use UTC timezone on PostgreSQL."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET TIME ZONE 'UTC';")
    cursor.close()


__all__ = [
    'AppenderQuery',
    'BaseIdNameMixin',
    'BaseMixin',
    'BaseNameMixin',
    'BaseScopedIdMixin',
    'BaseScopedIdNameMixin',
    'BaseScopedNameMixin',
    'CoordinatesMixin',
    'DynamicMapped',
    'GeonameModel',
    'LocaleType',
    'Mapped',
    'Model',
    'ModelBase',
    'NoIdMixin',
    'Query',
    'QueryProperty',
    'RegistryMixin',
    'RoleMixin',
    'TSVectorType',
    'TimestampMixin',
    'TimezoneType',
    'UrlType',
    'UuidMixin',
    'backref',
    'db',
    'declarative_mixin',
    'declared_attr',
    'hybrid_method',
    'hybrid_property',
    'postgresql',
    'relationship',
    'sa',
    'sa_exc',
    'sa_orm',
    'with_roles',
]
