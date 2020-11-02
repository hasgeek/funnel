from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union

from flask import Response

#: Type used to indicate that a decorator returns its decorated attribute
T = TypeVar('T')

#: Return type of the `migrate_user` and `migrate_profile` methods
OptionalMigratedTables = Optional[Union[List[str], Tuple[str], Set[str]]]

#: JSON and Jinja2 compatible dict type. Cannot be a strict definition because a JSON
#: structure can have a nested dict with the same rules, requiring recursion. Mypy does
#: not support recursive types: https://github.com/python/mypy/issues/731. Both JSON
#: and Jinja2 templates require the dictionary key to be a string.
RenderWithDict = Dict[str, Any]

#: Return type for @render_with decorated views
ReturnRenderWith = Union[
    RenderWithDict,  # A dict
    Tuple[RenderWithDict, int],  # Dict + status code
    Tuple[RenderWithDict, int, Dict[str, str]],  # Dict + status code + headers
    Response,  # Fully formed Response object
]

#: Return type for Flask views
ReturnView = Union[str, Tuple[str, int], Tuple[str, int, Dict[str, str]], Response]
