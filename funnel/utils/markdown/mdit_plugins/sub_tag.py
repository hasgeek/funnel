"""
Markdown-it-py plugin to introduce <sub> markup using ~subscript~.

Ported from
https://github.com/markdown-it/markdown-it-sub/blob/master/dist/markdown-it-sub.js
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping, Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from markdown_it.utils import OptionsDict

__all__ = ['sub_plugin']

TILDE_CHAR = '~'

WHITESPACE_RE = re.compile(r'(^|[^\\])(\\\\)*\s')
UNESCAPE_RE = re.compile(r'\\([ \\!"#$%&\'()*+,.\/:;<=>?@[\]^_`{|}~-])')


def tokenize(state: StateInline, silent: bool) -> bool:
    start = state.pos
    ch = state.src[start]
    maximum = state.posMax
    found = False

    if silent:
        return False

    if ch != TILDE_CHAR:
        return False

    # Don't run any pairs in validation mode
    if start + 2 >= maximum:
        return False

    state.pos = start + 1

    while state.pos < maximum:
        if state.src[state.pos] == TILDE_CHAR:
            found = True
            break
        state.md.inline.skipToken(state)

    if not found or start + 1 == state.pos:
        state.pos = start
        return False

    content = state.src[start + 1 : state.pos]

    # Don't allow unescaped spaces/newlines inside
    if WHITESPACE_RE.search(content) is not None:
        state.pos = start
        return False

    state.posMax = state.pos
    state.pos = start + 1

    # Earlier we checked "not silent", but this implementation does not need it
    token = state.push('sub_open', 'sub', 1)
    token.markup = TILDE_CHAR

    token = state.push('text', '', 0)
    token.content = UNESCAPE_RE.sub('$1', content)

    token = state.push('sub_close', 'sub', -1)
    token.markup = TILDE_CHAR

    state.pos = state.posMax + 1
    state.posMax = maximum
    return True


def sub_open(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: MutableMapping,
) -> str:
    return '<sub>'


def sub_close(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: MutableMapping,
) -> str:
    return '</sub>'


def sub_plugin(md: MarkdownIt) -> None:
    """Render ``~text~`` with a HTML ``<sub>`` tag (example: ``H~2~O``)."""
    md.inline.ruler.after('emphasis', 'sub', tokenize)
    md.add_render_rule('sub_open', sub_open)
    md.add_render_rule('sub_close', sub_close)
