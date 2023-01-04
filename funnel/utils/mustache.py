"""Mustache templating supoport."""

from copy import copy
import functools
import re
import types

from chevron import render as mustache_html

__all__ = ['mustache_html', 'mustache_md', 'markdown_escape']

escape_re = re.compile(r"""([\[\\\]{|}\(\)`~!@#$%^&*=+;:'"<>/,.?_-])""")


def markdown_escape(text):
    return escape_re.sub(r'\\1').strip()


_globals = copy(mustache_html.__globals__)
_globals['_html_escape'] = markdown_escape

mustache_md = types.FunctionType(
    mustache_html.__code__,
    _globals,
    name='mustache_md',
    argdefs=mustache_html.__defaults__,
    closure=mustache_html.__closure__,
)
mustache_md = functools.update_wrapper(mustache_md, mustache_html)
mustache_md.__module__ = __name__
mustache_md.__kwdefaults__ = copy(mustache_html.__kwdefaults__)
