"""Type annotations for Funnel."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
from uuid import UUID

from sqlalchemy.orm import Mapped
from typing_extensions import ParamSpec, Protocol
from werkzeug.wrappers import Response  # Base class for Flask Response

from coaster.sqlalchemy import Query

__all__ = [
    'T',
    'P',
    'ModelType',
    'UuidModelType',
    'Mapped',
    'OptionalMigratedTables',
    'ReturnRenderWith',
    'ReturnResponse',
    'ReturnView',
    'WrappedFunc',
    'ReturnDecorator',
    'ResponseType',
]

#: Type used to indicate type continuity within a block of code
T = TypeVar('T')
#: Type used to indicate parameter continuity within a block of code
P = ParamSpec('P')

#: Type used to bound Query to host model
_QM = TypeVar('_QM', bound='ModelType')


class ModelType(Protocol[_QM]):
    """Protocol class for models."""

    __tablename__: str
    query: Query[_QM]


class IdModelType(ModelType):
    """Protocol class for models."""

    id: Mapped[Union[int, UUID]]  # noqa: A003


class UuidModelType(IdModelType):
    """Protocol class for models with UUID column."""

    uuid: Mapped[UUID]


#: Flask response headers can be a dict or list of key-value pairs
ResponseHeaders = Union[Dict[str, str], List[Tuple[str, str]]]

#: Flask views accept a response status code that is either an int or a string
ResponseStatusCode = Union[int, str]

#: Flask views can return a Response, a string or a JSON dictionary
ResponseTypes = Union[
    str,  # A string (typically `render_template`)
    Response,  # Fully formed response object
    Dict[str, Any],  # JSON response
]

#: Return type for Flask views (formats accepted by :func:`~flask.make_response`)
ReturnView = Union[
    ResponseTypes,  # Only a response
    Tuple[ResponseTypes, ResponseStatusCode],  # Response + status code
    Tuple[ResponseTypes, ResponseHeaders],  # Response + headers
    Tuple[
        ResponseTypes, ResponseStatusCode, ResponseHeaders
    ],  # Response + status code + headers
]

#: Type used for functions and methods wrapped in a decorator
WrappedFunc = TypeVar('WrappedFunc', bound=Callable)
#: Return type for decorator factories
ReturnDecorator = Callable[[WrappedFunc], WrappedFunc]

#: Return type of the `migrate_user` and `migrate_profile` methods
OptionalMigratedTables = Optional[Union[List[str], Tuple[str], Set[str]]]

#: JSON and Jinja2 compatible dict type. Cannot be a strict definition because a JSON
#: structure can have a nested dict with the same rules, requiring recursion. Mypy does
#: not support recursive types: https://github.com/python/mypy/issues/731. Both JSON
#: and Jinja2 templates require the dictionary key to be a string.
RenderWithDict = Dict[str, object]

#: Return type for @render_with decorated views, a subset of Flask view return types
ReturnRenderWith = Union[
    RenderWithDict,  # A dict of template variables
    Tuple[RenderWithDict, int],  # Dict + HTTP status code
    Tuple[RenderWithDict, int, Dict[str, str]],  # Dict + status code + HTTP headers
    Response,  # Fully formed Response object
]

#: Return type for Response objects
ReturnResponse = Response

#: Response typevar
ResponseType = TypeVar('ResponseType', bound=Response)
