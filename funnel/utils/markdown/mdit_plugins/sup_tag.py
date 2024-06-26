"""
Markdown-it-py plugin to introduce <sup> markup using ^superscript^.

Ported from
https://github.com/markdown-it/markdown-it-sup/blob/master/dist/markdown-it-sup.js
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

__all__ = ['sup_plugin']

CARET_CHAR = '^'

WHITESPACE_RE = re.compile(r'(^|[^\\])(\\\\)*\s')
UNESCAPE_RE = re.compile(r'\\([ \\!"#$%&\'()*+,.\/:;<=>?@[\]^_`{|}~-])')


def tokenize(state: StateInline, silent: bool) -> bool:
    start = state.pos
    ch = state.src[start]
    maximum = state.posMax
    found = False

    if silent:
        return False

    if ch != CARET_CHAR:
        return False

    # Don't run any pairs in validation mode
    if start + 2 >= maximum:
        return False

    state.pos = start + 1

    while state.pos < maximum:
        if state.src[state.pos] == CARET_CHAR:
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
    token = state.push('sup_open', 'sup', 1)
    token.markup = CARET_CHAR

    token = state.push('text', '', 0)
    token.content = UNESCAPE_RE.sub('$1', content)

    token = state.push('sup_close', 'sup', -1)
    token.markup = CARET_CHAR

    state.pos = state.posMax + 1
    state.posMax = maximum
    return True


def sup_open(
    renderer: RendererHTML,  # noqa: ARG001
    tokens: Sequence[Token],  # noqa: ARG001
    idx: int,  # noqa: ARG001
    options: OptionsDict,  # noqa: ARG001
    env: EnvType,  # noqa: ARG001
) -> str:
    return '<sup>'


def sup_close(
    renderer: RendererHTML,  # noqa: ARG001
    tokens: Sequence[Token],  # noqa: ARG001
    idx: int,  # noqa: ARG001
    options: OptionsDict,  # noqa: ARG001
    env: EnvType,  # noqa: ARG001
) -> str:
    return '</sup>'


def sup_plugin(md: MarkdownIt) -> None:
    """Render ``^text^`` with a HTML ``<sup>`` tag (example: ``^2^H~2~O``)."""
    md.inline.ruler.after('emphasis', 'sup', tokenize)
    md.add_render_rule('sup_open', sup_open)
    md.add_render_rule('sup_close', sup_close)
