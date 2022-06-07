"""Type annotations for Funnel."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple, TypeVar, Union

from flask.typing import ResponseReturnValue
from werkzeug.wrappers import Response  # Base class for Flask Response

__all__ = [
    'OptionalMigratedTables',
    'ReturnRenderWith',
    'ReturnResponse',
    'ReturnView',
    'T',
]

#: Flask 2.0 replaces our previous custom definition of ReturnView
ReturnView = ResponseReturnValue

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
