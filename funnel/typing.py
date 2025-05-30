"""Type annotations for Funnel."""

from __future__ import annotations

from typing import ParamSpec, TypeAlias, TypeVar

from flask.typing import ResponseReturnValue
from werkzeug.wrappers import Response  # Base class for Flask Response

from coaster.views import ReturnRenderWith

__all__ = [
    'OptionalMigratedTables',
    'P',
    'ResponseReturnValue',
    'ResponseType',
    'ReturnRenderWith',
    'ReturnResponse',
    'ReturnView',
    'T',
    'T_co',
]

#: Type used to indicate type continuity within a block of code
T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
#: Type used to indicate parameter continuity within a block of code
P = ParamSpec('P')


#: Return type for Flask views (formats accepted by :func:`~flask.make_response`)
ReturnView: TypeAlias = ResponseReturnValue

#: Return type of the `migrate_user` and `migrate_profile` methods
OptionalMigratedTables: TypeAlias = list[str] | tuple[str] | set[str] | None

#: Return type for Response objects
ReturnResponse: TypeAlias = Response

#: Response typevar
ResponseType = TypeVar('ResponseType', bound=Response)
