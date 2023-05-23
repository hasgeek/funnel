"""Mustache templating support."""

from copy import copy
from typing import Callable
import functools
import types

from chevron import render
from markupsafe import escape as html_escape

from .markdown import markdown_escape

__all__ = ['mustache_html', 'mustache_md']


def _render_with_escape(
    name: str, escapefunc: Callable[[str], str]
) -> Callable[..., str]:
    """Make a copy of Chevron's render function with a replacement HTML escaper."""
    _globals = copy(render.__globals__)
    _globals['_html_escape'] = escapefunc

    new_render = types.FunctionType(
        render.__code__,
        _globals,
        name=name,
        argdefs=render.__defaults__,
        closure=render.__closure__,
    )
    new_render = functools.update_wrapper(new_render, render)
    new_render.__module__ = __name__
    new_render.__kwdefaults__ = copy(render.__kwdefaults__)
    return new_render


mustache_html = _render_with_escape('mustache_html', html_escape)
mustache_md = _render_with_escape('mustache_md', markdown_escape)
# TODO: Add mustache_mdhtml for use with Markdown with HTML tags enabled
