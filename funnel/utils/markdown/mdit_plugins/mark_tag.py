"""
Markdown-it-py plugin to introduce <mark> markup using ==marked==.

Ported from markdown_it.rules_inline.strikethrough.
"""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence

from markdown_it import MarkdownIt
from markdown_it.renderer import OptionsDict, RendererHTML
from markdown_it.rules_inline import StateInline
from markdown_it.rules_inline.state_inline import Delimiter
from markdown_it.token import Token

__all__ = ['mark_plugin']

EQUALS_CHAR = '='


def tokenize(state: StateInline, silent: bool) -> bool:
    """Insert each marker as a separate text token, and add it to delimiter list."""
    start = state.pos
    ch = state.src[start]

    if silent:
        return False

    if ch != EQUALS_CHAR:
        return False

    scanned = state.scanDelims(state.pos, True)

    length = scanned.length

    if length < 2:
        return False

    if length % 2:
        token = state.push('text', '', 0)
        token.content = ch
        length -= 1

    i = 0
    while i < length:
        token = state.push('text', '', 0)
        token.content = ch + ch
        state.delimiters.append(
            Delimiter(
                marker=ord(ch),
                length=0,  # disable "rule of 3" length checks meant for emphasis
                token=len(state.tokens) - 1,
                end=-1,
                open=scanned.can_open,
                close=scanned.can_close,
            )
        )
        i += 2

    state.pos += scanned.length
    return True


def _post_process(state: StateInline, delimiters: list[Delimiter]) -> None:
    lone_markers = []
    maximum = len(delimiters)

    for i in range(0, maximum):
        start_delim = delimiters[i]
        if start_delim.marker != ord(EQUALS_CHAR):
            i += 1
            continue

        if start_delim.end == -1:
            i += 1
            continue

        end_delim = delimiters[start_delim.end]

        token = state.tokens[start_delim.token]
        token.type = 'mark_open'
        token.tag = 'mark'
        token.nesting = 1
        token.markup = EQUALS_CHAR * 2
        token.content = ''

        token = state.tokens[end_delim.token]
        token.type = 'mark_close'
        token.tag = 'mark'
        token.nesting = -1
        token.markup = EQUALS_CHAR * 2
        token.content = ''

        end_token = state.tokens[end_delim.token - 1]

        if end_token.type == 'text' and end_token == EQUALS_CHAR:  # nosec
            lone_markers.append(end_delim.token - 1)

    # If a marker sequence has an odd number of characters, it's split
    # like this: `=====` -> `=` + `==` + `==`, leaving one marker at the
    # start of the sequence.
    #
    # So, we have to move all those markers after subsequent mark_close tags.
    #
    while lone_markers:
        i = lone_markers.pop()
        j = i + 1

        while j < len(state.tokens) and state.tokens[j].type == 'mark_close':
            j += 1

        j -= 1

        if i != j:
            token = state.tokens[j]
            state.tokens[j] = state.tokens[i]
            state.tokens[i] = token


def post_process(state: StateInline) -> None:
    """Walk through delimiter list and replace text tokens with tags."""
    tokens_meta = state.tokens_meta
    maximum = len(state.tokens_meta)
    _post_process(state, state.delimiters)
    curr = 0
    while curr < maximum:
        try:
            curr_meta = tokens_meta[curr]
        except IndexError:
            pass
        else:
            if curr_meta and 'delimiters' in curr_meta:
                _post_process(state, curr_meta["delimiters"])
        curr += 1


def mark_open(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: MutableMapping,
) -> str:
    return '<mark>'


def mark_close(
    renderer: RendererHTML,
    tokens: Sequence[Token],
    idx: int,
    options: OptionsDict,
    env: MutableMapping,
) -> str:
    return '</mark>'


def mark_plugin(md: MarkdownIt) -> None:
    """Render ``==text==`` markup with a HTML ``<mark>`` tag."""
    md.inline.ruler.before('strikethrough', 'mark', tokenize)

    md.inline.ruler2.before('strikethrough', 'mark', post_process)

    md.add_render_rule('mark_open', mark_open)
    md.add_render_rule('mark_close', mark_close)
