"""Mustache templating support."""

import functools
import types
from collections.abc import Callable
from copy import copy
from typing import TypeVar
from typing_extensions import ParamSpec

from chevron import render
from markupsafe import Markup, escape as html_escape

from .markdown import MarkdownString, markdown_escape

__all__ = ['mustache_html', 'mustache_md']


_P = ParamSpec('_P')
_T = TypeVar('_T', bound=str)


def _render_with_escape(
    name: str,
    renderer: Callable[_P, str],
    escapefunc: Callable[[str], str],
    recast: type[_T],
    doc: str | None = None,
) -> Callable[_P, _T]:
    """
    Make a copy of Chevron's render function with a replacement HTML escaper.

    Chevron does not allow the HTML escaper to be customized, so we construct a new
    function using the same code, replacing the escaper in the globals. We also recast
    Chevron's output to a custom sub-type of str like :class:`~markupsafe.Markup` or
    :class:`~funnel.utils.markdown.escape.MarkdownString`.

    :param name: Name of the new function (readable as `func.__name__`)
    :param renderer: Must be :func:`chevron.render` and must be explicitly passed for
        mypy to recognise the function's parameters
    :param escapefunc: Replacement escape function
    :param recast: str subtype to recast Chevron's output to
    :param doc: Optional replacement docstring
    """
    _globals = copy(renderer.__globals__)
    # Chevron tries `output += _html_escape(thing)`, which given Markup or
    # MarkdownString will call `thing.__radd__(output)`, which will then escape the
    # existing output. We must therefore recast the escaped string as a plain `str`
    _globals['_html_escape'] = lambda text: str(escapefunc(text))

    new_render = types.FunctionType(
        renderer.__code__,
        _globals,
        name=name,
        argdefs=renderer.__defaults__,
        closure=renderer.__closure__,
    )
    new_render = functools.update_wrapper(new_render, renderer)
    new_render.__module__ = __name__
    new_render.__kwdefaults__ = copy(renderer.__kwdefaults__)
    new_render.__doc__ = renderer.__doc__

    @functools.wraps(renderer)
    def render_and_recast(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        # pylint: disable=not-callable
        return recast(new_render(*args, **kwargs))

    render_and_recast.__doc__ = doc if doc else renderer.__doc__
    return render_and_recast


mustache_html = _render_with_escape(
    'mustache_html',
    render,
    html_escape,
    Markup,
    doc="Render a Mustache template in a HTML context.",
)
mustache_md = _render_with_escape(
    'mustache_md',
    render,
    markdown_escape,
    MarkdownString,
    doc="Render a Mustache template in a Markdown context.",
)
