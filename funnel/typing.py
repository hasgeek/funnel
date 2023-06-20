"""Type annotations for Funnel."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union

from flask.typing import ResponseReturnValue
from typing_extensions import ParamSpec
from werkzeug.wrappers import Response  # Base class for Flask Response

from coaster.views import ReturnRenderWith

__all__ = [
    'T',
    'P',
    'OptionalMigratedTables',
    'ReturnRenderWith',
    'ReturnResponse',
    'ReturnView',
    'WrappedFunc',
    'ReturnDecorator',
    'ResponseType',
    'ResponseReturnValue',
]

#: Type used to indicate type continuity within a block of code
T = TypeVar('T')
#: Type used to indicate parameter continuity within a block of code
P = ParamSpec('P')


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
ReturnView = ResponseReturnValue

#: Type used for functions and methods wrapped in a decorator
WrappedFunc = TypeVar('WrappedFunc', bound=Callable)
#: Return type for decorator factories
ReturnDecorator = Callable[[WrappedFunc], WrappedFunc]

#: Return type of the `migrate_user` and `migrate_profile` methods
OptionalMigratedTables = Optional[Union[List[str], Tuple[str], Set[str]]]

#: Return type for Response objects
ReturnResponse = Response

#: Response typevar
ResponseType = TypeVar('ResponseType', bound=Response)
