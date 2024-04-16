"""Model base class and shared imports."""

from __future__ import annotations

from typing import ClassVar

import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
import sqlalchemy.orm as sa_orm
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table
from sqlalchemy.dialects import postgresql
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


class Model(ModelBase, DeclarativeBase):
    """Base for all models."""

    __table__: ClassVar[Table]
    __with_timezone__ = True


class GeonameModel(ModelBase, DeclarativeBase):
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


__all__ = [
    'AppenderQuery',
    'backref',
    'BaseIdNameMixin',
    'BaseMixin',
    'BaseNameMixin',
    'BaseScopedIdMixin',
    'BaseScopedIdNameMixin',
    'BaseScopedNameMixin',
    'CoordinatesMixin',
    'db',
    'declarative_mixin',
    'declared_attr',
    'DynamicMapped',
    'GeonameModel',
    'hybrid_method',
    'hybrid_property',
    'LocaleType',
    'Mapped',
    'Model',
    'ModelBase',
    'NoIdMixin',
    'postgresql',
    'Query',
    'QueryProperty',
    'RegistryMixin',
    'relationship',
    'RoleMixin',
    'sa_exc',
    'sa_orm',
    'sa',
    'TimestampMixin',
    'TimezoneType',
    'TSVectorType',
    'UrlType',
    'UuidMixin',
    'with_roles',
]
