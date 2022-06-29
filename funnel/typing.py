"""Type annotations for Funnel."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple, TypeVar, Union
from uuid import UUID

from werkzeug.wrappers import Response  # Base class for Flask Response

from typing_extensions import Protocol

from coaster.sqlalchemy import Query

__all__ = [
    'ModelType',
    'UuidModelType',
    'OptionalMigratedTables',
    'ReturnRenderWith',
    'ReturnResponse',
    'ReturnView',
    'T',
]


class ModelType(Protocol):
    """Protocol class for models."""

    __tablename__: str
    __table_args__: tuple
    query: Query


class UuidModelType(ModelType):
    """Protocol class for models with UUID column."""

    uuid: UUID


#: Flask response headers can be a dict or list of key-value pairs
ResponseHeaders = Union[Dict[str, str], List[Tuple[str, str]]]

#: Flask views accept a response status code that is either an int or a string
ResponseStatusCode = Union[int, str]

#: Flask views can return a Response or a string
ResponseTypes = Union[
    str,  # A string (typically `render_template`)
    Response,  # Fully formed response object
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

#: Type used to indicate that a decorator returns its decorated attribute
T = TypeVar('T')

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
