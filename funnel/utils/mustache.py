"""Mustache templating supoport."""

from copy import copy
import functools
import re
import types

from chevron import render as mustache_html

__all__ = ['mustache_html', 'mustache_md', 'markdown_escape']

#: Based on the ASCII punctuation list in the CommonMark spec at
#: https://spec.commonmark.org/0.30/#backslash-escapes
escape_re = re.compile(r"""([\[\\\]{|}\(\)`~!@#$%^&*=+;:'"<>/,.?_-])""")


def markdown_escape(text):
    """
    Escape all Markdown formatting characters and strip whitespace at ends.

    As per the CommonMark spec, all ASCII punctuation can be escaped with a backslash
    and compliant parsers will then render the punctuation mark as a literal character.
    However, escaping any other character will cause the backslash to be rendered. This
    escaper therefore targets only ASCII punctuation characters listed in the spec.

    Edge whitespace is significant in Markdown and must be stripped when escaping as:

    * Four spaces at the start will initiate a code block
    * Two spaces at the end will cause a line-break in non-GFM Markdown

    Replacing these spaces with &nbsp; is not suitable because non-breaking spaces
    affect HTML rendering, specifically the CSS ``white-space: normal`` sequence
    collapsing behaviour.
    """
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
